"""Large compared word-channel UI integration; linked review required."""
NAME='ui_consolidated_c'
REQUIRES=()
CONFLICTS=()
ORACLES=()
CASE_KINDS=()
C_HARD_FLOAT=True
C_SOURCES=('sdk/nds/ui_consolidated/uc_ui_browser_draw.c', 'sdk/nds/ui_consolidated/uc_ui_browser_helpers.c', 'sdk/nds/ui_consolidated/uc_ui_browser_knobs.c', 'sdk/nds/ui_consolidated/uc_ui_browser_navigation.c', 'sdk/nds/ui_consolidated/uc_ui_context_callbacks.c', 'sdk/nds/ui_consolidated/uc_ui_effect_set.c', 'sdk/nds/ui_consolidated/uc_ui_effect_set_build.c', 'sdk/nds/ui_consolidated/uc_ui_exp_calibrate.c', 'sdk/nds/ui_consolidated/uc_ui_global_basic.c', 'sdk/nds/ui_consolidated/uc_ui_global_dispatch.c', 'sdk/nds/ui_consolidated/uc_ui_global_led.c', 'sdk/nds/ui_consolidated/uc_ui_global_lifecycle.c', 'sdk/nds/ui_consolidated/uc_ui_global_power.c', 'sdk/nds/ui_consolidated/uc_ui_global_power_sequence.c', 'sdk/nds/ui_consolidated/uc_ui_global_preset.c', 'sdk/nds/ui_consolidated/uc_ui_global_preset_apply.c', 'sdk/nds/ui_consolidated/uc_ui_home_layout.c', 'sdk/nds/ui_consolidated/uc_ui_home_levels.c', 'sdk/nds/ui_consolidated/uc_ui_looper_actions.c', 'sdk/nds/ui_consolidated/uc_ui_midi_transport.c', 'sdk/nds/ui_consolidated/uc_ui_task_setup.c', 'sdk/nds/ui_consolidated/uc_ui_window12.c', 'sdk/nds/ui_consolidated/uc_ui_window1_close.c', 'sdk/nds/ui_consolidated/uc_ui_window1_handlers.c', 'sdk/nds/ui_consolidated/uc_ui_window1_keys.c', 'sdk/nds/ui_consolidated/uc_ui_window1_knob.c', 'sdk/nds/ui_consolidated/uc_ui_window1_labels.c', 'sdk/nds/ui_consolidated/uc_ui_window1_status.c', 'sdk/nds/ui_consolidated/uc_ui_window1_tick.c', 'sdk/nds/ui_consolidated/uc_ui_window1_versions.c')
C_HARD_FLOAT_SOURCES=C_SOURCES
HOOKED=(121348, 121012, 121026, 121098, 121190, 121330, 121510, 129090, 129128, 129132, 123580, 127204, 127418, 123568, 129194, 138438, 112914, 112958, 112968, 112984, 112994, 113050, 113060, 113086, 113112, 113132, 113174, 113216, 113928, 114018, 114088, 114160, 114232, 114662, 115408, 117520, 117590, 117764, 112886, 113960, 114514, 114744, 114804, 135516, 135544, 135548, 135568, 135740, 135824, 136100, 136588, 136600, 162814, 162822, 162826, 162830, 162862, 162876, 162890, 162904, 162918, 162932, 162946, 162964, 164136, 164360, 164370, 163728, 163772, 164380, 164622, 163004, 163056, 163114, 163170, 163282, 163320, 163380, 163808, 163850, 163888, 164000, 164060, 163446, 163490, 163616, 163674, 136832, 137312, 137490, 129176, 129180, 129330, 129902, 131260, 131428, 134206, 92144, 92262, 92818, 92918, 162248, 162676, 106658, 106662, 106678, 106806, 106878, 107686, 109632, 109670, 153484, 147636, 147660, 147664, 147688, 147702, 147720, 147918, 147978, 148178, 148288, 149196, 150600, 149680, 151176, 153718, 150182)
C_ENTRIES=tuple(f'nds_uc_{a:05x}'for a in HOOKED)
CODE={}
DATA={}
HOOKS={}
def patches(c):
 return [(a,f'j {c.labels[f"nds_uc_{a:05x}"]:#x}',f'compared consolidated UI {a:05x}')for a in HOOKED]
