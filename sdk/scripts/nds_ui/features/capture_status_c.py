"""Paired capture successor component. No installation approval implied.
Startup BL is after zeroing and before 57d9a's setgie.e on normal startup.
The tiny bridge preserves the caller frame; cache reset needs masked entry.
"""
NAME='capture_status_c'
REQUIRES=('telemetry_c','gr_meter_c','host_layer_c')
CONFLICTS=()
ORACLES=()
CASE_KINDS=()
C_SOURCES=('sdk/capture_status/capture_status.c','sdk/capture_status/capture_link.c','sdk/capture_status/nds_dst_names.c')
# 2026-11-21 DST Capture Slot shows the capture name: stock fs0 hook entries, hard float (only stock code calls them).
C_HARD_FLOAT=True
C_HARD_FLOAT_SOURCES=('sdk/capture_status/nds_dst_names.c',)
C_ENTRIES=('gp50_capture_cache_reset','gp50_capture_cached_frame',
           'gp50_capture_link_request','gp50_capture_link_receive',
           'gp50_capture_cancel','gp50_capture_request',
           'gp50_dst_param_text','gp50_dst_param_text_stored')
def startup(c):
 c.begin('capture_startup')
 c.s.emit('jal 0x57c86\njal @gp50_capture_transport_reset')
 if 'footswitch_ab_c' in c.enabled:   # A/B footswitch state owner 255 (nothing loaded), before interrupts
  c.s.emit('jal @gp50_fs_ab_reset')
 if 'external_components_c' in c.enabled:
  c.s.emit('jal @gp50_components_init')
 c.end()
def param_text_stock(c):
 # Stock 0x43c92 after its hook: the displaced prologue (push25 s4,32 / mov55 s0,a0; push25 also sets s2 to its own
 # address, so s2 gets the stock one, as legacy_ui_c's 0x1d2c8 stub), then the stock body at 0x43c96. fs0 untouched.
 c.s.label('gp50_param_text_stock_43c92')
 c.s.emit('push25 s4,32\nmovi s2,0x43c92\nmov55 s0,a0\nj 0x43c96')
CODE={'startup':startup,'param_text_stock':param_text_stock}
DATA={}
HOOKS={}
def patches(c):
 seg=c.cfg['segment']
 # 224 = capture cache; 272 adds the 48-byte A/B footswitch state at 0x2001f580 (never the Wah/meter area 0x2001f450)
 if int(seg['state'],16)!=0x2001f4a0 or seg['state_bytes']!=(272 if 'footswitch_ab_c' in c.enabled else 224):
  raise ValueError('capture needs exact paired 64-byte cache reservation')
 at=0x57d94;old=bytes.fromhex('49ffff79')
 if c.parent_b[at-0x10000:at-0x10000+4]!=old:
  raise ValueError('capture startup call preimage mismatch')
 out=[(at,f'jal {c.labels["capture_startup"]:#x}','startup zero then capture reset before interrupt enable')]
 for a,pre,label,why in ((0x43c92,'fc4480c0','gp50_dst_param_text','parameter value text: DST Capture Slot shows the capture name, else stock'),
                         (0x43d36,'fc02b61f','gp50_dst_param_text_stored','stored parameter value text: as 0x43c92 (DST Capture name)')):
  if c.parent_b[a-0x10000:a-0x10000+4]!=bytes.fromhex(pre):raise ValueError(f'{a:#x} preimage mismatch')
  out.append((a,f'j {c.labels[label]:#x}',why))
 return out
