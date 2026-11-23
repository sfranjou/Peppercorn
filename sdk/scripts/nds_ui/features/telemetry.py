"""Telemetry transport (MOD030 schema 2 + MOD033 lease cache): GUI-tick service that admits
one coalesced 0x60f0 request, the receive validator/cache, the host read-class reply 0x51,
and the lease-block copy. Ported unchanged from scripts/build_nds_cpu_pct_code.py (MOD037).

State (STATE, 148 B) word offsets used here: +0 requested, +4 pending, +8 valid, +12 timeout,
+16 sent tick, +20 received tick, +24 rx count, +28 sent valid, +32..+68 cached fields,
+68 progress, +72 admit tick, +76 admit valid, +80 last kind, +84/+88 UI request tick/valid,
+92 fast mode (GR meter shown), +96..+136 lease cache (LEASE).
"""
import struct
from ..stock_api import API

NAME = 'telemetry'
REQUIRES = ()
ORACLES = ('sdk/telemetry/nds/model.py', 'sdk/telemetry/nds/model_lease.py')
CASE_KINDS = ('service', 'receive', 'host', 'gui', 'routing')


def section_gui(c):
    s = c.s
    c.begin('gui'); s.emit(f'jal {API.gui_link_receive_tick:#x}\nmov55 s0,a0\njal @service\nmov55 a0,s0'); c.end()


def section_dispatch(c):
    s = c.s
    s.label('dispatch'); s.emit(f'movi a0,0x60f0\nbeq a0,a5,@receive\nj {API.mod030_dispatch:#x}')


def section_read_route(c):
    s = c.s
    # Safe late read-class hook: original a0 selector and s1 length live.
    s.label('read_route'); s.emit(f'movi a1,0x51\nbne a0,a1,@route_original\nmovi a1,2\nbne s1,a1,@route_invalid\nmovi a0,12\nj {API.read_route_table_index:#x}')
    s.label('route_invalid'); s.emit(f'j {API.read_route_invalid:#x}')
    s.label('route_original'); s.emit(f'movi a1,0x4f\nbeq a0,a1,@route_4f\nj {API.read_route_original:#x}')
    s.label('route_4f'); s.emit(f'j {API.read_route_4f:#x}')


def section_service(c):
    s = c.s; STATE, LEGACY = c.STATE, c.LEGACY
    c.begin('service', 64); s.address('s1', STATE); s.address('s2', LEGACY); s.emit(f'jal {API.irq_guard_enter:#x}'); s.address('a0', API.tick_counter); s.emit('lwi s0,[a0 + 0]')
    # Only own software pending timeout; never release descriptor on timeout.
    for reg, timeout, key in [('s1', 1000, 'ext'), ('s2', 500, 'legacy')]:
        s.emit(f'lwi a0,[{reg} + 4]\nbeqz a0,@{key}_timeout_done\nlwi a0,[{reg} + 16]\nsub a0,s0,a0\nslti ta,a0,{timeout}\nbnez ta,@{key}_timeout_done\nmovi a0,0\nswi a0,[{reg} + 4]\nmovi a0,1\nswi a0,[{reg} + 12]'); s.label(key + '_timeout_done')
    s.emit('lwi a0,[s1 + 4]\nbnez a0,@service_exit\nlwi a0,[s2 + 4]\nbnez a0,@service_exit\nlwi a0,[s1 + 76]\nbeqz a0,@rate_ok\nlwi a0,[s1 + 72]\nsub a0,s0,a0\nlwi a1,[s1 + 92]\nbnez a1,@svc_fast\nslti ta,a0,500\nbnez ta,@service_exit\nj @rate_ok'); s.label('svc_fast'); s.emit('slti ta,a0,100\nbnez ta,@service_exit'); s.label('rate_ok')
    s.address('a0', API.link_tx_state); s.emit('lbi a0,[a0 + 16]\nbnez a0,@service_exit'); s.address('a0', API.link_queue_counters); s.emit('lhi a1,[a0 + 0]\nlhi a2,[a0 + 2]\nbne a1,a2,@service_exit\nslti ta,a1,12\nbeqz ta,@service_exit\nlwi a0,[s1 + 0]\nbeqz a0,@choose_legacy\nlwi a0,[s2 + 0]\nbeqz a0,@choose_ext\nlwi a0,[s1 + 80]\nbeqz a0,@choose_ext'); s.label('choose_legacy'); s.emit('lwi a0,[s2 + 0]\nbeqz a0,@service_exit\nmovi s3,0\nmov55 s4,s2\nj @admit'); s.label('choose_ext'); s.emit('movi s3,1\nmov55 s4,s1'); s.label('admit')
    s.emit(f'lwi s5,[s4 + 16]\nmovi a0,1\nswi a0,[s4 + 4]\nswi s0,[s4 + 16]\nbeqz s3,@legacy_send\nmovi a0,0x60f0\nshi a0,[sp + 40]\nmovi a0,12\nshi a0,[sp + 42]\nmovi a0,2\nswi a0,[sp + 44]\nmovi a0,0\nswi a0,[sp + 48]\nmovi a0,1\naddi a1,sp,40\nmovi a2,12\nmovi a3,0\njal {API.link_queue_produce:#x}\nj @sent'); s.label('legacy_send'); s.emit(f'jal {API.legacy_load_send:#x}'); s.label('sent'); s.emit('bnez a0,@send_reject\nmovi a0,0\nswi a0,[s4 + 0]\nswi a0,[s4 + 12]\nmovi a0,1\nbeqz s3,@legacy_sent_valid\nswi a0,[s1 + 28]\nj @global_admit'); s.label('legacy_sent_valid'); s.emit('swi a0,[s2 + 36]'); s.label('global_admit'); s.emit('swi s0,[s1 + 72]\nswi a0,[s1 + 76]\nswi s3,[s1 + 80]\nj @service_exit'); s.label('send_reject'); s.emit('movi a0,0\nswi a0,[s4 + 4]\nswi s5,[s4 + 16]'); s.label('service_exit'); s.emit(f'jal {API.irq_guard_leave:#x}'); c.end(64)


def section_receive(c):
    s = c.s; STATE = c.STATE
    # Receiver: CRC gate already passed. Validate entire shape and semantic invariants before guard.
    c.begin('receive'); s.emit('movi a0,84\nbne s0,a0,@receive_end'); s.address('s2', API.link_rx_frame)
    for off, v in [(1, 84), (2, 0), (3, 1), (4, 0xf0), (5, 0x60), (6, 80), (7, 0)]: s.emit(f'lbi a0,[s2 + {off}]\nmovi a1,{v}\nbne a0,a1,@receive_end')
    s.emit('lwi a0,[s2 + 8]\nmovi a1,2\nbne a0,a1,@receive_end\nlwi s3,[s2 + 12]\nlwi s4,[s2 + 16]\nslti ta,s4,16\nbeqz ta,@receive_end\nmovi a1,1\nand a0,s4,a1\nbnez a0,@arm_valid')
    for off in [12, 20, 24, 44]: s.emit(f'lwi a0,[s2 + {off}]\nbnez a0,@receive_end')
    s.emit('movi a1,8\nand a0,s4,a1\nbnez a0,@receive_end\nj @arm_checked'); s.label('arm_valid'); s.emit('movi a1,8\nand a0,s4,a1\nbeqz a0,@receive_end\nlwi a0,[s2 + 20]\nlwi a1,[s2 + 24]\nslt ta,a1,a0\nbnez ta,@receive_end'); s.label('arm_checked'); s.emit('movi a1,2\nand a0,s4,a1\nbnez a0,@dsp_valid')
    for off in [28, 32, 36, 40]: s.emit(f'lwi a0,[s2 + {off}]\nbnez a0,@receive_end')
    s.emit('j @dsp_checked'); s.label('dsp_valid'); s.emit('lwi a0,[s2 + 28]\nlwi a1,[s2 + 32]\nslt ta,a1,a0\nbnez ta,@receive_end'); s.label('dsp_checked'); s.emit('movi a1,4\nand a0,s4,a1\nbeqz a0,@current_checked\nmovi a1,3\nand a0,s4,a1\nbne a0,a1,@receive_end\nlwi a0,[s2 + 40]\nbne a0,s3,@receive_end'); s.label('current_checked'); s.emit('movi a1,8\nand a0,s4,a1\nbeqz a0,@frames_invalid\nmovi a1,1\nand a0,s4,a1\nbeqz a0,@receive_end\nlwi a0,[s2 + 44]\nmovi a1,64\nbne a0,a1,@receive_end\nj @validated'); s.label('frames_invalid'); s.emit('lwi a0,[s2 + 44]\nbnez a0,@receive_end'); s.label('validated')
    s.address('s1', STATE); s.emit('jal @lease_guard\nmovi a2,0\nlwi a0,[s1 + 8]\nbeqz a0,@progress_done\nlwi a0,[s1 + 32]\nsub a0,s3,a0\nbeqz a0,@progress_hold\nbltz a0,@progress_ambiguous\nj @progress_done'); s.label('progress_hold'); s.emit('movi a2,32\nj @progress_done'); s.label('progress_ambiguous'); s.emit('movi a2,64'); s.label('progress_done'); s.emit('swi a2,[s1 + 68]'); s.address('a0', API.tick_counter); s.emit('lwi a0,[a0 + 0]\nswi a0,[s1 + 20]')
    for off in range(0, 36, 4): s.emit(f'lwi a0,[s2 + {12 + off}]\nswi a0,[s1 + {32 + off}]')
    s.emit('lwi a0,[s1 + 24]\naddi a0,a0,1\nswi a0,[s1 + 24]\nmovi a0,1\nswi a0,[s1 + 8]\nlwi a0,[s1 + 4]\nbeqz a0,@receive_unlock'); s.address('a0', API.link_tx_state); s.emit(f'lbi a1,[a0 + 16]\nbeqz a1,@receive_unlock\nlhi a1,[a0 + 10]\nslti ta,a1,16\nbnez ta,@receive_unlock\nlwi a0,[a0 + 4]\nbeqz a0,@receive_unlock\nlhi a0,[a0 + 4]\nmovi a1,0x60f0\nbne a0,a1,@receive_unlock\nmovi a0,0\nswi a0,[s1 + 4]\nswi a0,[s1 + 12]\njal {API.link_release_owned:#x}'); s.label('receive_unlock'); s.emit(f'jal {API.irq_guard_leave:#x}'); s.label('receive_end'); c.end(tail=API.receive_continue)


def section_host(c):
    s = c.s; STATE = c.STATE
    # Host: fixed aligned48B stack reply and guarded cache snapshot. Refresh is coalesced after status snapshot.
    c.begin('host', 96); s.emit('mov55 s0,a0'); s.address('s1', STATE); s.emit(f'jal {API.irq_guard_enter:#x}\nlwi s2,[s1 + 8]\nlwi a0,[s1 + 4]\nslli a0,a0,1\nor s2,s2,a0\nlwi a0,[s1 + 0]\nslli a0,a0,2\nor s2,s2,a0\nlwi a0,[s1 + 12]\nslli a0,a0,3\nor s2,s2,a0\nlwi a0,[s1 + 8]\nbeqz a0,@host_empty\nlwi a0,[s1 + 68]\nor s2,s2,a0\nlwi a0,[s1 + 24]\nswi a0,[sp + 44]'); s.address('a0', API.tick_counter); s.emit('lwi a0,[a0 + 0]\nlwi a1,[s1 + 20]\nsub a0,a0,a1\nswi a0,[sp + 48]\nslti ta,a0,1000\nbnez ta,@host_fields\nori s2,s2,16'); s.label('host_fields')
    for off in range(0, 36, 4): s.emit(f'lwi a0,[s1 + {32 + off}]\nswi a0,[sp + {52 + off}]')
    s.emit('j @host_publish'); s.label('host_empty'); s.emit('movi a0,0\nswi a0,[sp + 44]')
    for off in range(52, 88, 4): s.emit(f'swi a0,[sp + {off}]')
    s.emit('movi a0,-1\nswi a0,[sp + 48]'); s.label('host_publish'); s.emit(f'movi a0,1\nswi a0,[s1 + 0]\njal {API.irq_guard_leave:#x}\nmovi a0,0x12\nsbi a0,[sp + 40]\nmovi a0,0x51\nsbi a0,[sp + 41]\nmovi a0,1\nsbi a0,[sp + 42]\nsbi s2,[sp + 43]\naddi a0,sp,40\nmovi a1,48\nmov55 a2,s0\njal {API.host_reply_serialize:#x}'); c.end(96)


def section_lease_guard(c):
    s = c.s
    # MOD033: lease block (36 B at frame +48) copied with the telemetry fields, inside the same guard.
    s.label('lease_guard'); s.emit(f'addi sp,sp,-8\nswi lp,[sp + 0]\njal {API.irq_guard_enter:#x}'); s.address('a3', c.LEASE)
    for i in range(9): s.emit(f'lwi a0,[s2 + {48 + 4 * i}]\nswi a0,[a3 + {4 * i}]')
    s.emit('movi a0,1\nswi a0,[a3 + 36]\nlwi lp,[sp + 0]\naddi sp,sp,8\nret5 lp')


def data_read_table(c):
    # Stock host read-class table (12 entries) copied from the parent, plus entry 12 = host.
    c.align(4)
    off = API.host_read_table - 0x10000
    table = c.parent_b[off:off + 48] + struct.pack('<I', c.labels['host'])
    c.data('read_table', table)


CODE = {'gui': section_gui, 'dispatch': section_dispatch, 'read_route': section_read_route,
        'service': section_service, 'receive': section_receive, 'host': section_host,
        'lease_guard': section_lease_guard}
DATA = {'read_table': data_read_table}


def patches(c):
    L = c.labels
    return [(API.hook_gui_receive_call, f'jal {L["gui"]:#x}', 'GUI tick: wrapper calls stock receive then service'),
            (API.hook_link_dispatch, f'j {L["dispatch"]:#x}', 'receiver command compare: 0x60f0 to own receive'),
            (API.hook_read_route, f'j {L["read_route"]:#x}', 'read-class selector 0x51 to table index 12'),
            (API.hook_read_table_hi, f'sethi a0,{L["read_table"] >> 12:#x}', 'read table base (hi)'),
            (API.hook_read_table_lo, f'ori a0,a0,{L["read_table"] & 4095:#x}', 'read table base (lo)')]
