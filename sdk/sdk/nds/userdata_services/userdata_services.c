/* Compared word-channel UserData helpers. Float-channel entries remain stock. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define userdata_drain_link nds_uds_467a2
#define userdata_catalog_a_send nds_uds_46842
#define userdata_catalog_b_send nds_uds_4685a
#define userdata_summary_send nds_uds_46872
#define userdata_sync_all nds_uds_46892
#define userdata_service_wait nds_uds_46bcc
#include "../../../firmware/reconstructed/nds/userdata_service.c"
#define userdata_preset_byte_notify_set nds_uds_472d8
#define userdata_order_move_notify nds_uds_47362
#define userdata_order_sequence_check nds_uds_4737a
#define userdata_order_sequence_set nds_uds_473b2
#define userdata_footswitch_mask_set nds_uds_47422
#define userdata_footswitch_target_set nds_uds_4743c
#define userdata_footswitch_action_set nds_uds_47492
#define userdata_preset_reload_notify nds_uds_47630
#include "../../../firmware/reconstructed/nds/userdata_order_control.c"
#define userdata_storage_refresh nds_uds_47a86
#define userdata_exp_flag_notify_set nds_uds_47aca
#define userdata_tempo_flag_notify_set nds_uds_47b50
#define userdata_exp_target_notify_set nds_uds_47c00
#define userdata_volume_min_notify_set nds_uds_47ebc
#define userdata_volume_max_notify_set nds_uds_47ed8
#define userdata_byte62_notify_set nds_uds_47efc
#include "../../../firmware/reconstructed/nds/userdata_side_notifications.c"
#define userdata_word14_notify_set nds_uds_46d50
#define userdata_pair38_notify_set nds_uds_46f02
#define userdata_boot_state_notify_set nds_uds_470e0
#include "../../../firmware/reconstructed/nds/userdata_word_notifications.c"
#define userdata_exp_mode_set nds_uds_46e88
#define userdata_tuner_mode_set nds_uds_46fb2
#define userdata_fx_test_mode_set nds_uds_4765a
#define userdata_fx_run_mode_set nds_uds_47696
#include "../../../firmware/reconstructed/nds/userdata_modes.c"
#define userdata_effect_changed nds_uds_473f0
#include "../../../firmware/reconstructed/nds/userdata_dispatch.c"
#define userdata_route_packet nds_uds_467ae
#include "../../../firmware/reconstructed/nds/userdata_route_packet.c"
