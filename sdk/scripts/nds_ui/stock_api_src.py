# Source table for stock_api.json (kept as Python for readable evidence strings); run
# `python3 -m nds_ui.stock_api --write` from scripts/ to regenerate the JSON.
F,D,H,C,R='function','data','hook_site','constant','parent_resident'
E_GR='analysis/firmware/GR_METER.md "Stock LVGL primitives identified" (home tile builder 0x27498..0x27630, work/nds_map/listings/gui_bar.txt, boot_win0.txt)'
E_GUARD='analysis/firmware/LOAD_BRIDGE_AUDIT.md (PSW save, setgie.d, nesting counter)'
E_TEL='analysis/firmware/NDS_BLOCK_TELEMETRY.md; analysis/firmware/LOAD_BRIDGE_IMPLEMENTATION.md'
E_CAT='analysis/firmware/NDS_EFFECT_CATALOG.md (item 9 phase B: entry redirected to the C catalog; original compared in work/firmware_source/nds_catalog*, nds_slot_tables)'
E_SLOT='analysis/firmware/NDS_EFFECT_CATALOG.md section 5; firmware/reconstructed/nds/slot_table.c (service called by the stock slot-table senders)'
E_CHAIN='analysis/firmware/NDS_PARAMETER_SET.md (item 9, MOD052: entry redirected to the C chains, sdk/nds/catalog/chains_target.c; original compared in work/firmware_source/nds_parameter_set, nds_effect_select, nds_effect_link, nds_host_param, nds_host_notify)'
E_UI='analysis/firmware/NDS_UI_INPUT.md (item 9 step 3, MOD053: entry redirected to the C UI input modules, sdk/nds/ui_input; original compared in work/firmware_source/nds_ui_knob, nds_ui_footswitch, nds_ui_effect_set, nds_input_scan)'
E_LEGACY='analysis/firmware/NDS_CODE_ROOM.md step 1 (MOD055: legacy UI assembly ported to C, feature legacy_ui_c; reach found by scripts/nds_legacy_reach.py on MOD054)'
E_HOST='analysis/firmware/NDS_CODE_ROOM.md section 8.2 (MOD056: host layer entry redirected to the C modules, sdk/nds/host_layer, feature host_layer_c; original compared in work/firmware_source/nds_host_*, nds_preset_*, nds_assign_refresh, nds_factory_reset)'
HOST_HOOKS=[0x1540a,0x15a1e,0x15b18,0x4085c,0x4089c,0x408de,0x408e8,0x40942,0x40a6e,0x40ad8,0x40b40,0x40ba8,0x41394,0x413be,0x414b2,0x418f0,0x41918,
 0x419f6,0x41dae,0x41dd2,0x41e68,0x41eb8,0x41edc,0x41f16,0x41f20,0x41f2a,0x42180,0x421ce,0x4220a,0x42328,0x42350,0x42394,0x423ba,0x42422,0x42488,
 0x424fc,0x4250a,0x42532,0x425de,0x425f4,0x4260a,0x426f6,0x42740,0x4278a,0x427ae,0x42820,0x429a0,0x429b4,0x429e6,0x42a26,0x42a98,0x42fd8,0x432a2,
 0x43374,0x435dc,0x43612,0x4364a,0x436d4,0x43724,0x43820,0x4385c,0x43876,0x438a6,0x438f0,0x43fa6,0x442f2,0x4468a,0x45f9c,0x47648,0x4787e,0x47c22,
 0x47d68,0x4965a,0x49772]
UI_HOOKS=[0x4772c,0x4586a,0x1c376,0x1be7e,0x157c4,0x157fc,0x15bc2,0x15cfc,0x17e8a]
CHAIN_HOOKS=[0x4557e,0x43a9e,0x43b2c,0x43ba6,0x43c20,0x453d0,0x466fe,0x466ac,0x46750,0x41dfe,0x4305e]
CATALOG_HOOKS=[0x1966a,0x19746,0x19782,0x198a2,0x1973a,0x19768,0x19774,0x197ac,0x197bc,0x198c4,0x1991e,0x197ca,0x1982e,0x43996,0x439b6,0x439dc,
 0x1996a,0x1997c,0x19984,0x1998a,0x19990,0x199b0,0x199de,0x199e2,0x19a12,0x19a4e,0x19b64,0x19b88,0x19bc2,0x19c00,0x19c5c,0x19c9a,
 0x19cd4,0x19ce6,0x19cee,0x19cf4,0x19cfa,0x19d42,0x19d62,0x19d90,0x19d96,0x19dc6,0x19e02,0x19f1c,0x19f40,0x19f7a,0x19fb8,0x1a014,0x1a052,0x1a08c]
ENTRIES=[
 # name, address, kind, signature, evidence
 ('irq_guard_enter',0x5c0e2,F,'void(void): nested interrupt disable (outermost PSW saved)',E_GUARD),
 ('irq_guard_leave',0x5c102,F,'void(void): nested interrupt restore',E_GUARD),
 ('link_queue_produce',0x15480,F,'int(a0=channel 1, a1=inner msg*, a2=len, a3=0): enqueue ARM link packet, 0=ok','analysis/firmware/NDS32_TRANSPORT.md "15480 builds the interprocessor packet"'),
 ('legacy_load_send',0x46262,F,'int(void): stock producer of 12-byte 0x6002 load request via 0x15480','analysis/firmware/LOAD_MEASUREMENT.md (producer table entry 25 at 0x140ea8)'),
 ('link_release_owned',0x1573e,F,'void(void): clear link descriptor busy (own pending only)','analysis/firmware/LOAD_BRIDGE_AUDIT.md (0x1573e clears busy)'),
 ('host_reply_serialize',0x40942,F,'void(a0=buf*, a1=len, a2=host ctx): queue host read-class reply','analysis/firmware/NDS32_TRANSPORT.md; analysis/firmware/USB_REPLY_STALL.md'),
 ('gui_link_receive_tick',0x46a0a,F,'int(void): GUI-task internal-link receive tick (return preserved by wrapper)','analysis/firmware/LINK_PROTOCOL.md; NDS32_APPLICATION_MAP.md'),
 ('effect_ordinal',0x475d0,F,'int(a0=group): current effect ordinal in group','LAB_NOTEBOOK.md 11 47 effect select (0x475d0/0x475d8); GR meter ordinal check'),
 ('lv_obj_create',0x293e0,F,'lv_obj_t*(parent)',E_GR),
 ('strip_label_show',0x293fc,F,'void(obj, 1): make MOD026 strip label visible (used after set_text since MOD026; exact LVGL name unconfirmed)','scripts/build_ui_assignment_code.py render/draw; NDSCpuPctStudy label-show model'),
 ('lv_obj_set_pos',0x2a46a,F,'void(obj, x, y)',E_GR),
 ('lv_obj_set_size',0x2a4ce,F,'void(obj, w, h)',E_GR),
 ('lv_obj_remove_style',0x2d03e,F,'void(obj, style=0, selector=0xffffff): remove all styles',E_GR),
 ('lv_obj_set_style_bg_color',0x2d886,F,'void(obj, rgb565 colour, selector)',E_GR),
 ('lv_obj_set_style_bg_opa',0x2d896,F,'void(obj, opa, selector)',E_GR),
 ('lv_obj_set_style_radius',0x2d9b6,F,'void(obj, radius, selector): selector 0 main part, 0x20000 indicator','MOD037 (LAB_NOTEBOOK 2026-10-19 square bar ends; work/mod037_nds/assembled.tsv; radius calls modeled in NDSCpuPctStudy)'),
 ('lv_obj_get_child',0x2da52,F,'lv_obj_t*(obj, index)',E_GR),
 ('lv_obj_del',0x2dbb4,F,'void(obj): delete object and children',E_GR),
 ('lv_bar_set_value',0x3da4c,F,'void(bar, value, anim=0)',E_GR),
 ('lv_bar_set_range',0x3db20,F,'void(bar, min, max)',E_GR),
 ('lv_label_create',0x3e78e,F,'lv_obj_t*(parent)',E_GR),
 ('lv_label_set_text',0x3eea0,F,'void(label, const char*)',E_GR),
 ('lv_bar_create',0x4076a,F,'lv_obj_t*(parent)',E_GR),
 ('read_route_table_index',0x435c4,F,'continuation: read-class with a0=table index (s1 length 2 checked)','analysis/firmware/NDS_BLOCK_TELEMETRY.md (hook 4357a after class/selector checks)'),
 ('read_route_invalid',0x435ca,F,'continuation: read-class invalid length','analysis/firmware/NDS_BLOCK_TELEMETRY.md'),
 ('read_route_original',0x4357e,F,'continuation: instruction after hook site 0x4357a (original selector path)','analysis/firmware/NDS_BLOCK_TELEMETRY.md'),
 ('read_route_4f',0x435a2,F,'continuation: stock selector 0x4f branch target','analysis/firmware/NDS_BLOCK_TELEMETRY.md'),
 ('receive_continue',0x46b7a,F,'continuation: link receiver default release after own 0x60f0 handler','analysis/firmware/LOAD_BRIDGE_IMPLEMENTATION.md'),
 ('tick_counter',0x20004ad0,D,'u32 raw application tick (SysTickInc 0x174e8)','analysis/firmware/NDS32_APPLICATION_MAP.md Tick sources'),
 ('link_tx_state',0x2000a4f4,D,'link descriptor: +4 frame ptr, +10 u16 length, +16 u8 busy','analysis/firmware/NDS32_TRANSPORT.md; LOAD_BRIDGE_AUDIT.md'),
 ('link_queue_counters',0x20008cc0,D,'u16 producer +0, u16 consumer +2; 12 slots x 516 B','analysis/firmware/NDS32_TRANSPORT.md'),
 ('link_rx_frame',0x20010928,D,'internal-link receive frame buffer (84 B telemetry reply)',E_TEL),
 ('mdata_enable_mask',0x200106c5,D,'u32 LE unaligned block enable mask; effect ids u32 at +14+4g','analysis/firmware/ADMISSION.md; NDS32_APPLICATION_MAP.md mData table'),
 ('host_read_table',0x140bb0,D,'12 x u32 host read-class (12 xx) reply builders; relocated copy +entry 12','analysis/firmware/NDS32_HOST_DISPATCH.md'),
 ('version_string',0x140f34,D,'NUL-terminated version text (M1.1.0x), patched by scripts/ui_theme.py','scripts/ui_theme.py; review_mod037_cpu_pct.py'),
 ('gp',0x20011658,C,'global pointer value','analysis/firmware/LOAD_BRIDGE_AUDIT.md'),
 ('LV_PART_INDICATOR',0x20000,C,'LVGL v8 style selector part indicator','LVGL v8 lv_obj.h; MOD037 radius call'),
 ('MDATA_IDS_OFFSET',14,C,'effect id array offset from mdata_enable_mask','analysis/firmware/ADMISSION.md'),
 ('hook_gui_receive_call',0x27b3c,H,'stock jal 0x46a0a in GUI task loop','analysis/firmware/NDS_HOOK_TOOLING.md table'),
 ('hook_link_dispatch',0x46ab6,H,'stock movi a0,0x7004 receiver compare','analysis/firmware/NDS_HOOK_TOOLING.md table'),
 ('hook_read_route',0x4357a,H,'read-class selector branch','analysis/firmware/NDS_BLOCK_TELEMETRY.md'),
 ('hook_read_table_hi',0x429ce,H,'sethi a0 of read table base pair','analysis/firmware/NDS32_HOST_DISPATCH.md'),
 ('hook_read_table_lo',0x429d2,H,'ori a0 of read table base pair','analysis/firmware/NDS32_HOST_DISPATCH.md'),
 ('hook_window4_close',0x1d2bc,H,'window 4 (effect edit) close entry (MOD026 hook site)','analysis/firmware/NDS32_APPLICATION_MAP.md; GR_METER.md'),
 ('hook_window4_tick',0x1d2c8,H,'window 4 (effect edit) tick entry (MOD026 hook site)','analysis/firmware/NDS32_APPLICATION_MAP.md'),
 ('hook_bss_end',0x57ca2,H,'startup zero-end a2=GP+off (paired with heap start)','analysis/firmware/NDS_HOOK_TOOLING.md'),
 ('hook_capture_startup',0x57d94,H,'startup jal 0x57c86: zero reserved application state before capture reset and interrupt enable','analysis/firmware/CAPTURE_STARTUP_READER_AUDIT.md; scripts/nds_ui/features/capture_status_c.py'),
 ('hook_heap_start',0x5ceec,H,'heap start a1=GP+off','analysis/firmware/NDS_HOOK_TOOLING.md'),
 # Admission refusal (2026-10-20): the three choke points every user-initiated block/model change passes
 ('enable_get',0x452ae,F,'int(a0=group): current enable bit of group (0 for group >= 10)','analysis/firmware/ADMISSION_REFUSAL.md (call sites from the fixed NDS export listing)'),
 ('select_apply',0x453d0,F,'int(a0=group, a1=ordinal): apply a model selection; 0 = rejected/unchanged','analysis/firmware/NDS32_USERDATA.md 0x453d0'),
 ('effect_count',0x43996,F,'int(a0=group): number of models in group (catalog; groups 4/9 own tables)','analysis/firmware/NDS32_USERDATA.md 0x43996'),
 ('effect_id_for',0x439b6,F,'u32(a0=group, a1=ordinal): public id of a model','analysis/firmware/NDS32_USERDATA.md 0x439b6'),
 ('footswitch_toggle',0x4586a,F,'void(a0=footswitch 0/1): toggle its assigned blocks (mask ^= assignment)','analysis/firmware/ADMISSION_REFUSAL.md (call sites from the fixed NDS export listing)'),
 ('footswitch_assign',0x2001083d,D,'u32 LE unaligned x2: block mask assigned to footswitch 0/1 (mData+0x1f5)','analysis/firmware/ADMISSION_REFUSAL.md (call sites from the fixed NDS export listing); 0x4586a reads gp-0x1010+(idx+0x7c)*4+5'),
 ('preset_name_text',0x472b8,F,'const char*(void): current preset name (0x451ac: gp-0xfa1 = mData+0x6f); the stock home title text MOD029 restores','work/processing_meter source (restore: jal 0x472b8 then set_text ctx+0x34)'),
 ('hook_enable_get_call',0x473f6,H,'jal 0x452ae inside 0x473f0 (UI 0x1c5f8, host 11 49): a1 = requested state','analysis/firmware/ADMISSION_REFUSAL.md (call sites from the fixed NDS export listing)'),
 ('hook_link_full_config_call',0x463de,H,'jal 0x15480 inside 0x46366 (link cmd 0, full config 368 bytes)','analysis/firmware/LINK_PROTOCOL.md; analysis/tone_capture/TWO_CAPTURES_20261108.md (v7 link filter)'),
 ('hook_link_enable_call',0x466a2,H,'jal 0x15480 inside 0x46678 (link cmd 4, one block on/off)','analysis/firmware/LINK_PROTOCOL.md; analysis/tone_capture/TWO_CAPTURES_20261108.md (v7 link filter)'),
 ('hook_link_mask_call',0x4666e,H,'jal 0x15480 inside 0x4664c (link cmd 6, enable mask)','analysis/firmware/LINK_PROTOCOL.md; analysis/tone_capture/TWO_CAPTURES_20261108.md (v7 link filter)'),
 ('hook_link_model_call',0x46746,H,'jal 0x15480 inside 0x466fe (link cmd 5, model + parameters)','analysis/firmware/LINK_PROTOCOL.md; analysis/tone_capture/TWO_CAPTURES_20261108.md (v7 link filter)'),
 ('hook_select_apply_call',0x475de,H,'jal 0x453d0 inside 0x475d8 (UI 0x1c634, host 11 47)','analysis/firmware/ADMISSION_REFUSAL.md (call sites from the fixed NDS export listing)'),
 ('hook_footswitch_call',0x47456,H,'jal 0x4586a inside 0x47452 (9 footswitch call sites)','analysis/firmware/ADMISSION_REFUSAL.md (call sites from the fixed NDS export listing)'),
 # Code/data installed by earlier MODs, living in the parent's resident area
 # 0x16c6c0..0x170000. Valid only for parents that contain them (checked against the parent).
 ('mod030_dispatch',0x16c6e6,R,'MOD030 receive compare trampoline (legacy 0x6002 path)','work/load_measurement/implementation/labels.tsv dispatch'),
 # Diagnostics block in C (MOD056+, feature diagnostics_c; NDS_CODE_ROOM.md section 8.3): the stock-side reaches into the
 # MOD002/007/016/030 block 0x16c6c0..0x16cb60 found by scripts/nds_legacy_reach.py (lo 0x16c6c0) on MOD055/MOD056 b.
 ('hook_diag_usb_guard',0x431dc,H,'jal 0x4cf34 (USB bulk send) in the host reply path; MOD007: jal usb guard (busy byte set around the send)','analysis/firmware/USB_REPLY_STALL.md edit 1; firmware/reconstructed/nds/diagnostics.c diag_usb_guard'),
 ('hook_diag_host_word',0x140bc8,H,'read-class table word 6 (12 50) of the stock table 0x140bb0; MOD002: load bridge host reply (dead since MOD056: the parser uses own_read_table)','analysis/firmware/LOAD_BRIDGE_IMPLEMENTATION.md; firmware/reconstructed/nds/diagnostics.c diag_host'),
 ('hook_diag_peek_word',0x140c1c,H,'set-class table word (11 15); MOD016: main-memory peek','analysis/firmware/NDS_ASM_TO_C_INVENTORY.md; firmware/reconstructed/nds/diagnostics.c diag_peek'),
 ('mod026_window4_close',0x16e01c,R,'MOD026 window-4 close wrapper (chains stock close); GR close tail','work/ui_assignment_v2/labels.json close'),
 ('mod026_restore_ctx',0x16e39c,R,'void(ctx): restore MOD026 strip/title','work/ui_assignment_v2/labels.json restore'),
 ('mod026_set_text',0x16e52c,R,'void(label, text): set text only if changed','work/ui_assignment_v2/labels.json set_text'),
 ('mod026_editor_tick',0x16e948,R,'int(ctx, msg): MOD026 window-4 editor tick','work/ui_assignment_v2/labels.json editor_tick'),
 ('mod029_meter_refresh',0x16f556,R,'MOD029 home meter refresh (superseded; its call sites are rebound)','work/processing_meter/labels.json refresh'),
 ('mod029_meter_refresh_calls',[0x16f41e,0x16f47a,0x16efcc],R,'jal sites of the meter refresh (home tick, DRUM, MOD026 title restore)','work/processing_meter/spec.tsv, work/ui_assignment_v3/spec.tsv'),
 ('mod026_assign_state',0x2001f3f0,R,'u32 MOD026 assignment phase (0 = none)','scripts/build_ui_assignment_code.py STATE'),
 ('mod029_display_mode',0x2001f470,R,'u32 DRUM display mode (0 off, 1 ARM, 2 DSP, 3 MEM)','work/processing_meter; MOD033 MEM page'),
 ('link_post',0x4650e,F,'void(a0=msg*, a1=len, a2=wait, a3=queue): post an internal-link message (copied)',E_SLOT),
 ('heap_alloc',0x5cfb0,F,'void*(size): application heap allocation, 0 on failure',E_SLOT),
 ('heap_free',0x5cfd8,F,'void(ptr): application heap release',E_SLOT),
 ('link_mode_set',0x46622,F,'void(index): link selector write (0x17 before a slot upload, 0x18 after; wrappers 0x46cb8/0x46cc2)',E_SLOT),
 ('link_pace',0x467a2,F,'void(void): wait/poll between queued link deletes',E_SLOT),
 ('slot_notice_apply',0x46c9a,F,'void(a, b): N->S notice bytes 5/6 (0x1a08c)',E_SLOT),
]+[('hook_catalogf_%05x'%a,a,H,'stock float-result catalog/slot entry (fs0); 4-byte j to the hard-float C wrapper (cfg c_hard_float)',E_CAT) for a in (0x198f2,0x19c2e,0x19fe6)]+[('hook_catalog_%05x'%a,a,H,'stock catalog/slot-table entry; 4-byte j to the C wrapper nds_cat_/nds_slot_%05x'%a,E_CAT) for a in CATALOG_HOOKS]+[('hook_chain_%05x'%a,a,H,'stock effect-chain entry (hard float); 4-byte j to the C wrapper nds_chain_%05x (cfg c_chains)'%a,E_CHAIN) for a in CHAIN_HOOKS]+[('hook_ui_%05x'%a,a,H,'stock UI input entry; 4-byte j to the C function nds_ui_%05x (feature ui_input_c)'%a,E_UI) for a in UI_HOOKS]+[('hook_host_%05x'%a,a,H,'stock host-layer entry; 4-byte j to the C function nds_host_%05x (feature host_layer_c)'%a,E_HOST) for a in HOST_HOOKS]+[('hook_legacy_'+n,a,H,s,E_LEGACY) for n,a,s in (
 ('window4_open',0x1cc5c,'stock window-4 open entry (push25); MOD026: j to the open prologue-replay stub (assignment reset, 22-entry table)'),
 ('editor_table_hi',0x1cc62,'sethi a0 of the window-4 message table (MOD026: 22-entry editor table)'),
 ('editor_table_lo',0x1cc66,'ori a0 of the window-4 message table'),
 ('home_table_hi',0x21e4a,'sethi a0 of the home window message table (MOD029: 26-entry table; count at 0x21e46)'),
 ('home_table_lo',0x21e4e,'ori a0 of the home window message table'),
 ('home_tick',0x224f2,'stock home window tick entry (push25); MOD029: j to assign_tick'),
 ('preset_read',0x43fbc,'jal 0x4972e (preset slot read) in the preset load path; MOD029: jal assign_preset_read'),
 ('stage_copy',0x496ac,'memcpy jal in stock sector staging; MOD029: jal assign_stage_copy'),
 ('user_poll',0x49c7e,'jal 0x49b52 in the User_Msg task loop; MOD027: jal wah_poll'))]

# MOD058: original scalar reply entries, each a four-byte tail jump into the
# compared C serializer. Pin original bytes independently of generated wrappers.
ENTRIES += [('hook_scalar_%05x' % a,a,H,
 'u32(a0=value,a1=queue_flags); scalar reply entry tail-jump into compared C',
 'analysis/firmware/APPLICATION_CONTINUATION_20261025.md; work/firmware_source/nds_protocol_scalar_packets; feature protocol_scalars_c')
 for a in [265318, 265372, 265426, 265480, 265534, 265588, 265638, 265688, 265738, 265788, 265838, 265888, 265938, 265988, 266038, 266088, 266138, 266188, 266238, 266288, 266338, 266388, 266438, 266488, 266538, 266588, 266638, 266688, 266738, 266788, 266838, 266888, 266938, 266988, 267056, 267106]]

# MOD058 application helpers. Entries157c4/157fc retain the existing ui_input_c hooks.
ENTRIES += [('hook_application_%05x'%a,a,H,'stock entry tail jump to compared C; arguments/results pinned by per-study image proof','analysis/firmware/MOD058_APPLICATION_C_20261025.md; feature application_helpers_c')for a in [83994, 84160, 84614, 84638, 84748, 84792, 84850, 85578, 85584, 85590, 85666, 85812, 85818, 85832, 85846, 85852, 85870, 86064, 86078, 86084, 86196, 86262, 86328, 86344, 86350, 86374, 86388, 86406, 86412, 86460, 86474, 86674, 86742, 86782, 86938, 86958, 86964, 87762, 87768, 87808, 87852, 87870, 87878, 87886, 87892, 87992, 88212, 88354, 88496, 88536, 88546, 89764, 89868, 89890, 89912, 89934, 89940, 90070, 90204, 90412, 90434, 90520, 90886, 91096, 91322, 91540, 93716, 93734, 93778, 93948, 94376, 94714, 94738, 94764, 94788, 94848, 94946, 95080, 95092, 95098, 95138, 95150, 95170, 95192, 95224, 95252, 95318, 95330, 95400, 95464, 95476, 95482, 95488, 95528, 95568, 95584, 95600, 96358, 96622, 96648, 96698, 96714, 96940, 97230, 97236, 97896, 274476, 274818, 275190, 301676, 302418, 302776, 302804, 302824, 302850, 303252]]

# C prototypes for sdk/nds/stock_api.h (generated by `stock_api.py --write`). Only routines with a
# C prototype are callable from C; continuations and hook sites stay assembly-only.
C_PROTOTYPES={
 'link_post':'void link_post(const uint8_t *msg,uint32_t len,uint32_t wait,uint32_t queue)',
 'heap_alloc':'void *heap_alloc(uint32_t size)',
 'heap_free':'void heap_free(void *ptr)',
 'link_mode_set':'void link_mode_set(uint32_t index)',
 'link_pace':'void link_pace(void)',
 'slot_notice_apply':'void slot_notice_apply(uint32_t a,uint32_t b)',
 'irq_guard_enter':'void irq_guard_enter(void)',
 'irq_guard_leave':'void irq_guard_leave(void)',
 'link_queue_produce':'int link_queue_produce(uint32_t channel,const void *msg,uint32_t len,uint32_t zero)',
 'legacy_load_send':'int legacy_load_send(void)',
 'link_release_owned':'void link_release_owned(void)',
 'host_reply_serialize':'void host_reply_serialize(const void *buf,uint32_t len,void *host_ctx)',
 'gui_link_receive_tick':'int gui_link_receive_tick(void)',
 'effect_ordinal':'int effect_ordinal(uint32_t group)',
 'lv_obj_create':'lv_obj_t *lv_obj_create(lv_obj_t *parent)',
 'strip_label_show':'void strip_label_show(lv_obj_t *label,uint32_t one)',
 'lv_obj_set_pos':'void lv_obj_set_pos(lv_obj_t *o,int32_t x,int32_t y)',
 'lv_obj_set_size':'void lv_obj_set_size(lv_obj_t *o,int32_t w,int32_t h)',
 'lv_obj_remove_style':'void lv_obj_remove_style(lv_obj_t *o,void *style,uint32_t selector)',
 'lv_obj_set_style_bg_color':'void lv_obj_set_style_bg_color(lv_obj_t *o,uint32_t rgb565,uint32_t selector)',
 'lv_obj_set_style_bg_opa':'void lv_obj_set_style_bg_opa(lv_obj_t *o,uint32_t opa,uint32_t selector)',
 'lv_obj_set_style_radius':'void lv_obj_set_style_radius(lv_obj_t *o,int32_t r,uint32_t selector)',
 'lv_obj_get_child':'lv_obj_t *lv_obj_get_child(lv_obj_t *o,int32_t index)',
 'lv_obj_del':'void lv_obj_del(lv_obj_t *o)',
 'lv_bar_set_value':'void lv_bar_set_value(lv_obj_t *bar,int32_t v,int anim)',
 'lv_bar_set_range':'void lv_bar_set_range(lv_obj_t *bar,int32_t min,int32_t max)',
 'lv_label_create':'lv_obj_t *lv_label_create(lv_obj_t *parent)',
 'lv_label_set_text':'void lv_label_set_text(lv_obj_t *label,const char *text)',
 'lv_bar_create':'lv_obj_t *lv_bar_create(lv_obj_t *parent)',
 'mod026_restore_ctx':'void mod026_restore_ctx(void *edit_ctx)',
 'enable_get':'uint32_t enable_get(uint32_t group)',
 'select_apply':'uint32_t select_apply(uint32_t group,uint32_t ordinal)',
 'effect_count':'uint32_t effect_count(uint32_t group)',
 'effect_id_for':'uint32_t effect_id_for(uint32_t group,uint32_t ordinal)',
 'footswitch_toggle':'void footswitch_toggle(uint32_t index)',
 'preset_name_text':'const char *preset_name_text(void)',
 'mod026_set_text':'void mod026_set_text(lv_obj_t *label,const char *text)',
 'mod026_editor_tick':'int mod026_editor_tick(void *edit_ctx,void *msg)',
}

# MOD059 further compared application entries.
ENTRIES += [('hook_more_%05x'%a,a,H,'stock entry tail jump to compared C; image ABI proof required','feature application_more_c; MOD059 work in progress')for a in [84644, 84882, 85228, 85300, 85692, 85888, 94002, 97272, 299750, 299776, 299794, 299816, 300102, 300132, 300164, 300192, 300452, 300724, 300766, 300804, 300822, 300846, 300880, 300946, 301022, 301170, 301192, 301906, 302168]]

# MOD060 owned robustness fix; replaces faulty stock zero-interval behavior.
ENTRIES += [("hook_safe_tap",0x27ed0,H,"home tap entry to guarded C; valid-domain equivalence and owned zero policy","feature tap_safe_c; pending image review")]

# MOD063 compared Data public entries; explicit hard-float adapters.
ENTRIES += [('hook_data_%05x'%a,a,H,'stock Data entry to compared C; fs0 adapters where required','feature data_access_c; scripts/verify_nds_data_access_image.py')for a in [276994, 277060, 277218, 277244, 277262, 280164, 280182, 280192, 280238, 280244, 280252, 280258, 280264, 280276, 280290, 280372, 280386, 280462, 280538, 280544, 280566, 280572, 280598, 280604, 280640, 280646, 280662, 280668, 280698, 280704, 280740, 280746, 280752, 280778, 280808, 280844, 280858, 280878, 280884, 280900, 280906, 280932, 280952, 280980, 280986, 281008, 281060, 281198, 281212, 281666, 281672, 281690, 281696, 281714, 281720, 281730, 281764, 281790, 281806, 281826, 281854, 281912, 281942, 281966, 281972, 282010, 282028, 282078, 282092, 282112, 282118, 282128, 282198, 282258, 282432, 282484, 282548, 282574, 282596, 282602, 282630, 282636, 282662, 282668, 282684, 282690, 282706, 282724, 282778, 282882, 283024, 283030, 283052, 283058, 283076, 283106, 283112, 283134, 283152, 283176, 283196, 283272, 283310, 283354, 283388, 283472, 283584, 283994, 284024, 284390, 284396, 284504, 284602, 284634, 284670, 284934, 284954, 285008, 285022, 285030, 285108, 285114, 285160, 285168, 285256, 285306, 285312, 285334, 285406, 285476, 285496, 285512, 285558, 285564, 285640, 285652, 285658, 285682, 285688, 285712, 285796, 285810, 285942, 285956, 285992, 286006, 286126, 286132, 286138, 286144, 286150, 286156]]

# MOD064 integer UserData forwarding entries (float wrappers excluded).
ENTRIES += [('hook_ud_%05x'%a,a,H,'integer UserData public entry to compared C','scripts/study_nds_userdata_access.py')for a in [289826, 289834, 289842, 289946, 290058, 290088, 290120, 290180, 290188, 290224, 290260, 290290, 290320, 290360, 290396, 290432, 290554, 290592, 290634, 290642, 290668, 290730, 290890, 290916, 290924, 290984, 291008, 291016, 291024, 291032, 291060, 291092, 291138, 291192, 291222, 291270, 291278, 291286, 291512, 291520, 291528, 291536, 291578, 291674, 291808, 291816, 291892, 291978, 292288, 292296, 292346, 292392, 292434, 292494, 293530, 293538, 293570, 293614, 293656, 293724, 293880, 293914, 294232, 294240, 294500, 294528, 294572, 294580, 294644]]

# MOD065 compared UserData event/packet entries; image proofs required before handover.
ENTRIES += [('hook_ude_%05x'%a,a,H,'UserData event public entry to compared C','scripts/verify_mod065_userdata_events.py; stock routine study')for a in [287264, 287298, 287330, 287374, 287466, 287504, 287718, 287754, 287790, 287834, 287878, 287976, 288332, 288958, 289012, 289028, 289068, 289074, 289090, 289112, 289128, 289154, 289168, 289180, 289214, 289796, 289874, 289888, 289976, 289986, 289996, 290008, 290066, 290096, 290196, 290232, 290268, 290298, 290368, 290404, 290616, 290650, 290676, 290694, 290704, 290830, 290858, 290898, 290932, 291068, 291100, 291146, 291200, 291230, 294508, 294536, 294832]]

# MOD066 compared UserData float/field and home formatter entries; image proofs required.
ENTRIES += [("hook_udf_%05x"%a,a,H,"UserData field/float public ABI to compared C","feature userdata_fields_c; explicit fs0 adapters")for a in [288014, 288032, 288070, 288094, 288120, 288142, 288164, 288186, 288212, 288238, 288266, 289764, 289772, 289818, 289850, 289858, 289866, 289912, 289954, 290600, 290608, 290992, 291000, 291262, 291800, 291866, 292384, 293546, 293554, 293562, 294556, 294682]]
ENTRIES += [("hook_home_value_c",0x21ac2,H,"home value display entry to compared C","feature home_value_c; actual double/variadic-stack composition proof")]

# MOD066 compared rendering entries; no UI service replacement.
ENTRIES += [("hook_render_%05x"%a,a,H,"stock display rendering entry to compared C","feature ui_render_c; exact image stack/varargs proof required")for a in [0x1fc78,0x25ab0]]

# MOD067 compared table-format entries; incoming fs0 and existing text interface.
ENTRIES += [("hook_tables_%05x"%a,a,H,"parameter text table public float ABI to compared C","feature parameter_tables_c; exact image and text composition required")for a in [98144, 98186, 98228, 98270, 98312, 98354, 98396, 98438, 98480, 98522, 98564, 98606, 98648, 98690, 98732, 98774, 98816, 98858, 98900, 98942, 98984, 99026, 99068, 99110, 99152, 99194, 99236, 99278, 99320, 99362, 99404, 99446, 99488, 99530, 99572, 99614, 99656, 99698, 99740, 99782, 99824, 99866, 99908, 99950, 99992, 100034, 100076, 100118, 100160, 100202, 100244, 100286, 100328, 100370, 100412, 100454, 100496, 100538, 100580, 100622, 100664, 100706, 100748, 100790, 100832, 100874, 100916, 100936, 100978, 101020, 101062, 101104, 101146, 101188, 101230, 101272, 101314, 101356, 101398, 101440, 101482, 101524, 101566, 101608, 101650, 101692, 101734, 101776, 101818, 101860, 101902, 101944, 101986, 102028, 102070, 102112]]

# Compared formatting adapters; same parameter text interface, incoming fs0 ABI.
ENTRIES += [("hook_pfmt_%05x"%a,a,H,"parameter formatting public ABI to compared C","feature parameter_formats_c; exact image contracts required")for a in [102448, 102464, 102480, 102534, 102588, 102604, 102620, 102636, 102652, 102668, 102720, 102752, 102768, 102784, 102800, 102816, 102870, 102886, 102902, 102958, 103014, 103030, 103046, 103062, 103078, 103094, 103110, 103126, 103142, 103158, 103174, 103190, 103206, 103222, 103238, 103254, 103270, 103286, 103302, 103318, 103334, 103350, 103402, 103434, 103466, 103482, 103538, 103618, 103634, 103650, 103666, 103682, 103698, 103714, 103766, 103782, 103830, 103846, 103862, 103878, 103894, 103948, 103964, 103992, 104034, 104038]]

# Compared window constructors; exact linked proofs required before handover.
ENTRIES += [("hook_open_%05x"%a,a,H,"window constructor public entry to compared C","feature ui_open_c; ordered helpers, float transfers, stack varargs")for a in [131494, 155998, 127534, 152262]]

# MOD072 selected word-channel UserData services; float-channel helpers remain stock.
ENTRIES += [("hook_services_%05x"%a,a,H,"UserData word-channel service entry to compared C","feature userdata_services_c; ordered notifications, modes and transport packets")for a in [288674, 288686, 288834, 288858, 288882, 288914, 289740, 290128, 290440, 290562, 290738, 291040, 291544, 291682, 291706, 291762, 291824, 291874, 291900, 291986, 292400, 292442, 292502, 293510, 293578, 293712, 293888, 294588, 294616, 294652]]

# MOD073 compared home navigation, mode, press/release callbacks.
ENTRIES += [("hook_hcb_%05x"%a,a,H,"home callback public entry to compared C","feature home_callbacks_c; preserves existing theme and original callback interfaces")for a in [136604, 136608, 136630, 136648, 136682, 136716, 136730, 136744, 140518, 136758, 138010, 138484, 138542, 138662, 138154]]

ENTRIES += [("hook_window_common_%05x"%a,a,H,"window/common public entry to compared C","feature window_common_c; linked composition required")for a in [95608, 95704, 95794, 95904, 95910, 95988, 96066, 96072, 96134, 96158, 96170, 96246, 96322, 161968, 162028, 162088, 162128, 162152, 162532]]

# MOD075 integer-channel settings/order/expression control.
ENTRIES += [("hook_data_control_%05x"%a,a,H,"Data control public entry to compared C","feature data_control_c; float-channel routines excluded")for a in [277854, 277870, 277886, 277898, 278070, 278096, 278112, 278352, 286364, 281106, 285718, 285824, 286042, 286180]]

ENTRIES += [("hook_widget_builders_%05x"%a,a,H,"Widget builder public ABI to compared C","feature widget_builders_c; composition review required")for a in [160628, 160838, 161650, 161798]]

# MOD077 compared widget core/layout word-channel public entries.
ENTRIES += [("hook_widget_adapters_%05x"%a,a,H,"Widget adapter public ABI to compared C","feature widget_adapters_c; linked composition review required")for a in [159758, 159770, 159822, 159874, 159892, 159916, 159934, 159956, 159996, 160036, 160376, 160814, 160906, 161320, 161332, 161392, 161438, 161460, 161482, 161498, 161520, 161560, 161586, 161610, 160388, 160434, 160480, 160502, 160524, 160564, 160586, 160770]]

# Consolidated word-channel UI entry declarations.
ENTRIES += [("hook_uicons_%05x"%a,a,H,"Compared UI public entry","feature ui_consolidated_c; parent modifications excluded")for a in [121348, 121012, 121026, 121098, 121190, 121330, 121510, 129090, 129128, 129132, 123580, 127204, 127418, 123568, 129194, 138438, 112914, 112958, 112968, 112984, 112994, 113050, 113060, 113086, 113112, 113132, 113174, 113216, 113928, 114018, 114088, 114160, 114232, 114662, 115408, 117520, 117590, 117764, 112886, 113960, 114514, 114744, 114804, 135516, 135544, 135548, 135568, 135740, 135824, 136100, 136588, 136600, 162814, 162822, 162826, 162830, 162862, 162876, 162890, 162904, 162918, 162932, 162946, 162964, 164136, 164360, 164370, 163728, 163772, 164380, 164622, 163004, 163056, 163114, 163170, 163282, 163320, 163380, 163808, 163850, 163888, 164000, 164060, 163446, 163490, 163616, 163674, 136832, 137312, 137490, 129176, 129180, 129330, 129902, 131260, 131428, 134206, 92144, 92262, 92818, 92918, 162248, 162676, 106658, 106662, 106678, 106806, 106878, 107686, 109632, 109670, 153484, 147636, 147660, 147664, 147688, 147702, 147720, 147918, 147978, 148178, 148288, 149196, 150600, 149680, 151176, 153718, 150182]]

# Bulk application entry declarations (generated from compared study contracts).
ENTRIES.append(("hook_bulk_16ea4", 0x16ea4, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_4215c", 0x4215c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_4215e", 0x4215e, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_49db0", 0x49db0, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_49f1a", 0x49f1a, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_44a8a", 0x44a8a, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_44afa", 0x44afa, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_44bf0", 0x44bf0, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_43c92", 0x43c92, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_43d36", 0x43d36, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1786c", 0x1786c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_17a16", 0x17a16, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_17acc", 0x17acc, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_49236", 0x49236, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_178ac", 0x178ac, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_4933e", 0x4933e, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_49382", 0x49382, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_49414", 0x49414, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_494c2", 0x494c2, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_494fc", 0x494fc, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_49542", 0x49542, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_49d7a", 0x49d7a, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_49fba", 0x49fba, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_491fe", 0x491fe, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_497a8", 0x497a8, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_497f6", 0x497f6, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_499e8", 0x499e8, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_49a72", 0x49a72, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_49e50", 0x49e50, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_498a6", 0x498a6, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_4990e", 0x4990e, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_49982", 0x49982, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_49ac8", 0x49ac8, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_49b16", 0x49b16, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_18f0a", 0x18f0a, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1575c", 0x1575c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_15c36", 0x15c36, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_15e9e", 0x15e9e, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_14c34", 0x14c34, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_148c6", 0x148c6, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_46a0a", 0x46a0a, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_15480", 0x15480, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_15548", 0x15548, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_16254", 0x16254, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_155fe", 0x155fe, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_15646", 0x15646, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1630c", 0x1630c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_16354", 0x16354, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_163e4", 0x163e4, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_16436", 0x16436, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_16072", 0x16072, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_16520", 0x16520, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_165e2", 0x165e2, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_16fba", 0x16fba, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_4261e", 0x4261e, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_431ba", 0x431ba, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_431e8", 0x431e8, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_43254", 0x43254, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_4328e", 0x4328e, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_432ec", 0x432ec, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_4334c", 0x4334c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_49ff6", 0x49ff6, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_170de", 0x170de, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1712a", 0x1712a, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_15428", 0x15428, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_161ae", 0x161ae, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_49d44", 0x49d44, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_49a1c", 0x49a1c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_49d92", 0x49d92, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1e6a8", 0x1e6a8, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1da04", 0x1da04, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1d8b4", 0x1d8b4, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1d8c2", 0x1d8c2, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1d90a", 0x1d90a, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1d966", 0x1d966, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1d9f2", 0x1d9f2, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1daa6", 0x1daa6, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1f842", 0x1f842, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1f868", 0x1f868, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1f86c", 0x1f86c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1e2bc", 0x1e2bc, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1f0e4", 0x1f0e4, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1f1ba", 0x1f1ba, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1db4c", 0x1db4c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1e2b0", 0x1e2b0, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1f8aa", 0x1f8aa, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_21cc6", 0x21cc6, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1ae2c", 0x1ae2c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1ae30", 0x1ae30, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1ae3c", 0x1ae3c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1ae4c", 0x1ae4c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1ae98", 0x1ae98, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1aee0", 0x1aee0, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1af04", 0x1af04, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1af42", 0x1af42, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1af7c", 0x1af7c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1afb6", 0x1afb6, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1afea", 0x1afea, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1b0a6", 0x1b0a6, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1b0c2", 0x1b0c2, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1b13e", 0x1b13e, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1b21a", 0x1b21a, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1b730", 0x1b730, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1b73c", 0x1b73c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1cc5c", 0x1cc5c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1d2bc", 0x1d2bc, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1cb6c", 0x1cb6c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1ba8c", 0x1ba8c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1c70a", 0x1c70a, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1b912", 0x1b912, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1b93e", 0x1b93e, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1b948", 0x1b948, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1b958", 0x1b958, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1b962", 0x1b962, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1b99a", 0x1b99a, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1b9a4", 0x1b9a4, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1b9be", 0x1b9be, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1b9d8", 0x1b9d8, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1b9ec", 0x1b9ec, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1ba16", 0x1ba16, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1ba40", 0x1ba40, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1bd08", 0x1bd08, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1bd62", 0x1bd62, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1bda8", 0x1bda8, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1bdf0", 0x1bdf0, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1be38", 0x1be38, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1bfe6", 0x1bfe6, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1c128", 0x1c128, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1c2d0", 0x1c2d0, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1cb10", 0x1cb10, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1cb56", 0x1cb56, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1cc04", 0x1cc04, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1b8f6", 0x1b8f6, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1bd28", 0x1bd28, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1bf52", 0x1bf52, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1c038", 0x1c038, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1c074", 0x1c074, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1c1b2", 0x1c1b2, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1d2c8", 0x1d2c8, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_2115c", 0x2115c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_21178", 0x21178, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_2117c", 0x2117c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_21190", 0x21190, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_2123c", 0x2123c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_21290", 0x21290, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_21318", 0x21318, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_213a4", 0x213a4, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_2158c", 0x2158c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_21598", 0x21598, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_47452", 0x47452, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27bfe", 0x27bfe, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27c06", 0x27c06, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27c0a", 0x27c0a, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27c0e", 0x27c0e, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27c2e", 0x27c2e, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27c3c", 0x27c3c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27c4a", 0x27c4a, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27c58", 0x27c58, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27c66", 0x27c66, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27c74", 0x27c74, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27c82", 0x27c82, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27c94", 0x27c94, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_28128", 0x28128, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_28208", 0x28208, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_28212", 0x28212, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27f90", 0x27f90, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27fbc", 0x27fbc, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_2821c", 0x2821c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_2830e", 0x2830e, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27cbc", 0x27cbc, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27cf0", 0x27cf0, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27d2a", 0x27d2a, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27d62", 0x27d62, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27dd2", 0x27dd2, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27df8", 0x27df8, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27e34", 0x27e34, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27fe0", 0x27fe0, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_2800a", 0x2800a, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_28030", 0x28030, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_280a0", 0x280a0, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_280dc", 0x280dc, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27e76", 0x27e76, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27ea2", 0x27ea2, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27f20", 0x27f20, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27f5a", 0x27f5a, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_218a0", 0x218a0, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_21a38", 0x21a38, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_219be", 0x219be, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_219d0", 0x219d0, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_21a06", 0x21a06, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_21a12", 0x21a12, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_21a8c", 0x21a8c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_21680", 0x21680, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_21860", 0x21860, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_21912", 0x21912, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_21960", 0x21960, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_21e44", 0x21e44, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1f898", 0x1f898, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1f89c", 0x1f89c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1f932", 0x1f932, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1fb6e", 0x1fb6e, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_200bc", 0x200bc, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_20164", 0x20164, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_20c3e", 0x20c3e, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_201a6", 0x201a6, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1f978", 0x1f978, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1f9fc", 0x1f9fc, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1fb9e", 0x1fb9e, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_20c64", 0x20c64, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_16920", 0x16920, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_169ac", 0x169ac, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_16a00", 0x16a00, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_16a4a", 0x16a4a, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_16b58", 0x16b58, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_16b94", 0x16b94, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_16bd0", 0x16bd0, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_16c0c", 0x16c0c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_16c48", 0x16c48, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_16c88", 0x16c88, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_16cca", 0x16cca, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_16d14", 0x16d14, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_16d56", 0x16d56, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_16d90", 0x16d90, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_16dd2", 0x16dd2, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_167f0", 0x167f0, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_16866", 0x16866, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_16a92", 0x16a92, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_16af6", 0x16af6, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_16630", 0x16630, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1666a", 0x1666a, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_166b6", 0x166b6, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_166f2", 0x166f2, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_16746", 0x16746, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_16788", 0x16788, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_168dc", 0x168dc, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_228b6", 0x228b6, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_228ba", 0x228ba, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_22986", 0x22986, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_2299e", 0x2299e, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_22a5c", 0x22a5c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_22a60", 0x22a60, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_22a7c", 0x22a7c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_22a8a", 0x22a8a, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_22b28", 0x22b28, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_22b7e", 0x22b7e, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_279c8", 0x279c8, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27b74", 0x27b74, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27af0", 0x27af0, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27b42", 0x27b42, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_25994", 0x25994, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_25998", 0x25998, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_25a5a", 0x25a5a, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_26e7a", 0x26e7a, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_259a6", 0x259a6, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_26ea4", 0x26ea4, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_2601c", 0x2601c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_26f02", 0x26f02, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27132", 0x27132, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27498", 0x27498, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_27870", 0x27870, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_22be0", 0x22be0, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_22be4", 0x22be4, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_22e28", 0x22e28, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_22e46", 0x22e46, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_22e64", 0x22e64, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_22e82", 0x22e82, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_22e9c", 0x22e9c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_22eba", 0x22eba, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_22f00", 0x22f00, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_22ff6", 0x22ff6, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_2361a", 0x2361a, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_23648", 0x23648, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_23040", 0x23040, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1a0a2", 0x1a0a2, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1a0a6", 0x1a0a6, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1a0b6", 0x1a0b6, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1a136", 0x1a136, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1a17e", 0x1a17e, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1a22a", 0x1a22a, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1a264", 0x1a264, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1a4a6", 0x1a4a6, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1a620", 0x1a620, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1ac40", 0x1ac40, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_1ac66", 0x1ac66, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_2578c", 0x2578c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_240b4", 0x240b4, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_240cc", 0x240cc, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_240d0", 0x240d0, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_240e8", 0x240e8, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_240f6", 0x240f6, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_24108", 0x24108, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_241ce", 0x241ce, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_2420a", 0x2420a, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_242d2", 0x242d2, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_24340", 0x24340, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_246cc", 0x246cc, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_24c48", 0x24c48, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_248b0", 0x248b0, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_24e88", 0x24e88, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_25876", 0x25876, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_24aa6", 0x24aa6, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_236e4", 0x236e4, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_236e8", 0x236e8, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_236f6", 0x236f6, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_23744", 0x23744, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_23756", 0x23756, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_237b4", 0x237b4, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_237f8", 0x237f8, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_23876", 0x23876, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_238b4", 0x238b4, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_23950", 0x23950, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_239a0", 0x239a0, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_239ca", 0x239ca, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_23a28", 0x23a28, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_23a76", 0x23a76, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_23ac0", 0x23ac0, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_23f92", 0x23f92, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_23f9e", 0x23f9e, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_23fa2", 0x23fa2, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_23fd8", 0x23fd8, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_23aea", 0x23aea, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_471e8", 0x471e8, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_4722a", 0x4722a, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_47302", 0x47302, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_474ae", 0x474ae, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_47526", 0x47526, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_47860", 0x47860, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_47af6", 0x47af6, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_47b20", 0x47b20, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_47b64", 0x47b64, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_46622", 0x46622, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_47ea4", 0x47ea4, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_46c80", 0x46c80, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_46caa", 0x46caa, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_46ce4", 0x46ce4, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_46e18", 0x46e18, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_479d4", 0x479d4, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_47a22", 0x47a22, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_47a36", 0x47a36, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_47f22", 0x47f22, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_47f7c", 0x47f7c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_47fc2", 0x47fc2, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_4194e", 0x4194e, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_196a8", 0x196a8, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))
ENTRIES.append(("hook_bulk_196d8", 0x196d8, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))

ENTRIES.append(("hook_bulk_1499c", 0x1499c, H, "Bulk application public entry; focused integration verification required", "feature application_bulk_c; linked review required"))

# MOD082 optional public leaves: separate prefix keeps older c_chains unchanged.
ENTRIES += [('hook_remaining_chain_%05x' % a, a, H,
             'Original effect-chain ABI; optional c_remaining_chains public C entry',
             'analysis/firmware/REMAINING_CHAINS_ABI_20261027.md; original listing and compared chain sources')
            for a in (0x43a62, 0x43ac0, 0x43d52, 0x43a32, 0x45396,
                      0x43a80, 0x476e4, 0x427f8, 0x44cb8, 0x46fa2,
                      0x45744, 0x45944, 0x456cc)]

# MOD085 public notification and selection adapters; selection preserves linked admission.
ENTRIES += [('hook_notify_select_%05x' % a, a, H,
             'Original notify/select ABI; c_notify_select_chains public C entry; selection through admission',
             'analysis/firmware/NEXT_NOTIFY_SELECT_IMPLEMENTATION_PLAN.md; original listing and direct-image studies')
            for a in (0x40a42,0x40bbc,0x40be8,0x40c10,0x40c42,0x413f8,0x4145e,
                      0x4206a,0x420a0,0x420d4,0x42120,0x427d2,0x452a8,0x4578e,0x45958,0x47602,
                      0x430b8,0x45382,0x453ba,0x46bf4,0x46bfc,0x475d0,0x475d8)]

# Combined remaining application adapters. Shared assertion body hook preserves
# 4215c's two-byte push; reset tail remains original and cannot be reclaimed.
ENTRIES += [('hook_remaining_%05x'%a,a,H,'public remaining application adapter',
             'analysis/firmware/REMAINING_CONTROL_TARGET_DRAFT.md; standalone target studies')
            for a in (0x14bf6,0x14fd6,0x18f0a,0x41f34,0x46336,0x46366,0x464b2,0x46678,0x467fe,0x471de,0x46a0a,0x16ea4,0x4215e,0x49d92,0x49ff6)]
ENTRIES += [(n,a,F,s,'analysis/firmware/REMAINING_CONTROL_TARGET_DRAFT.md; original reset/assert/task disassembly')
            for n,a,s in (('stock_queue_receive',0x5ced2,'queue receive(queue,event,timeout)'),
                          ('stock_audio_notification',0x49d7a,'audio event notification'),
                          ('stock_fatal',0xd0b02,'fatal(file,line,expression,detail)'),
                          ('stock_reset_tail',0x4a070,'reset CSR/MMIO terminal continuation; entered on original frame'))]
C_PROTOTYPES.update({'stock_queue_receive':'uint32_t stock_queue_receive(uint32_t queue, uint16_t *event, uint32_t timeout)',
                     'stock_audio_notification':'void stock_audio_notification(void)',
                     'stock_fatal':'void stock_fatal(uint32_t file, uint32_t line, uint32_t expression, uint32_t detail)',
                     'stock_reset_tail':'void stock_reset_tail(void)'})

ENTRIES += [("hook_about_text_append",0x1f088,H,"last jal 0xd0da4 (bounded strcat, cap 100) building the Global settings About text (Firmware Version + version + copyright) before lv_label_set_text_fmt 0x3ef1a; SDK about lines are appended","LAB_NOTEBOOK 2026-11-05 (About page found after MOD136: 0x24aa6 is the window-1 test screen)")]
ENTRIES += [("hook_settings_table_register",0x1f23c,H,"window-9 open: jal 0x177aa (handler table 0xd5b50, 9 entries); the feature tile wrapper registers its own table",'LAB_NOTEBOOK 2026-11-06 (Global settings window 9: open 0x1f22e, handler table 0xd5b50, item loop 0x1f5b8..0x1f83e)'),
 ("hook_settings_item_loop",0x1f60e,H,"window-9 item loop: beqc r11,#2 (page 3 skips slot 4); replaced by j 0x1f808 so every page builds 4 tiles",'LAB_NOTEBOOK 2026-11-06 (Global settings window 9: open 0x1f22e, handler table 0xd5b50, item loop 0x1f5b8..0x1f83e)'),
 ("hook_settings_item_label",0x1f812,H,"window-9 item loop: jal 0x15f0c (UI text 0x43 + tile index) for each tile label",'LAB_NOTEBOOK 2026-11-06 (Global settings window 9: open 0x1f22e, handler table 0xd5b50, item loop 0x1f5b8..0x1f83e)')]
