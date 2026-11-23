/* Compared UserData forwarding/field notifications; explicit public float ABI. */
#define GP50_CATALOG_DIRECT 1
#define GP50_UD_FLOAT_LOCAL static inline __attribute__((always_inline))
#pragma GCC optimize("no-jump-tables")
#define userdata_param_value_bits owned_fields_userdata_param_value_bits
#define userdata_param_minimum_bits owned_fields_userdata_param_minimum_bits
#define userdata_param_maximum_bits owned_fields_userdata_param_maximum_bits
#define userdata_param_text_stored nds_udf_46c4a
#define userdata_level_a_bits owned_fields_userdata_level_a_bits
#define userdata_level_b_bits owned_fields_userdata_level_b_bits
#define userdata_group_parameter_count nds_udf_46be4
#define userdata_algo_entry nds_udf_46bec
#define userdata_exp_value_raw_forward nds_udf_46f28
#define userdata_exp_calibrate_forward nds_udf_46f30
#define userdata_level_d_set_bits owned_fields_userdata_level_d_set_bits
#define userdata_level_d_bits owned_fields_userdata_level_d_bits
#define userdata_ui_refresh_forward nds_udf_471be
#define userdata_preset_order_state nds_udf_473d8
#define userdata_switch_mask nds_udf_4741a
#define userdata_preset_dirty nds_udf_47620
#define userdata_catalog_flag_a nds_udf_47aaa
#define userdata_catalog_flag_b nds_udf_47ab2
#define userdata_catalog_flag_b_set nds_udf_47aba
#define userdata_exp_mask_state_forward nds_udf_47e9c
#define userdata_version_check_forward nds_udf_47f1a
#define userdata_send_buffer nds_udf_4650e
#define userdata_send_field nds_udf_46520
#define userdata_float_a_notify nds_udf_46546
#define userdata_float_b_notify nds_udf_4655e
#define userdata_byte40_notify nds_udf_46578
#define userdata_byte41_notify nds_udf_4658e
#define userdata_byte42_notify nds_udf_465a4
#define userdata_offset43_notify nds_udf_465ba
#define userdata_expression_notify nds_udf_465d4
#define userdata_constant_notify nds_udf_465ee
#define userdata_float_a_notify_alias nds_udf_4660a
#include "../../../firmware/reconstructed/nds/userdata_float_access.c"
#include "../../../firmware/reconstructed/nds/userdata_extra_adapters.c"
#include "../../../firmware/reconstructed/nds/userdata_field_notify.c"
float nds_udf_46c1a(uint32_t a0, uint32_t a1) {union {float f; uint32_t u;} word={.u=owned_fields_userdata_param_value_bits(a0, a1, (const StockIo *)0)};return word.f;}
float nds_udf_46c3a(uint32_t a0, uint32_t a1) {union {float f; uint32_t u;} word={.u=owned_fields_userdata_param_minimum_bits(a0, a1, (const StockIo *)0)};return word.f;}
float nds_udf_46c42(uint32_t a0, uint32_t a1) {union {float f; uint32_t u;} word={.u=owned_fields_userdata_param_maximum_bits(a0, a1, (const StockIo *)0)};return word.f;}
float nds_udf_46c78(void) {union {float f; uint32_t u;} word={.u=owned_fields_userdata_level_a_bits((const StockIo *)0)};return word.f;}
float nds_udf_46ca2(void) {union {float f; uint32_t u;} word={.u=owned_fields_userdata_level_b_bits((const StockIo *)0)};return word.f;}
float nds_udf_470b8(void) {union {float f; uint32_t u;} word={.u=owned_fields_userdata_level_d_bits((const StockIo *)0)};return word.f;}
uint32_t nds_udf_470b0(float value) {union {float f;uint32_t u;} word={.f=value};return owned_fields_userdata_level_d_set_bits(word.u,(const StockIo *)0);}
