/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define data_exp_calibrate bulk_data_expression_data_exp_calibrate
#define data_exp_curve bulk_data_expression_data_exp_curve
#define data_exp_value_ratio bulk_data_expression_data_exp_value_ratio
#define data_exp_value_raw bulk_data_expression_data_exp_value_raw
#define data_exp_target_set bulk_data_expression_data_exp_target_set
#define data_exp_parameter_set bulk_data_expression_data_exp_parameter_set
#define data_exp_mask_state bulk_data_expression_data_exp_mask_state
#define data_version_check bulk_data_expression_data_version_check
#include "../../../firmware/reconstructed/nds/data_expression.c"
float nds_bulk_44a8a(float value0) {union {float f;uint32_t u;} floatword0={.f=value0};union {float f;uint32_t u;} result={.u=bulk_data_expression_data_exp_curve(floatword0.u,(const StockIo *)0)};return result.f;}
uint32_t nds_bulk_44afa(uint32_t a0,float value0) {(void)a0;union {float f;uint32_t u;} floatword0={.f=value0};return bulk_data_expression_data_exp_value_ratio(a0,floatword0.u,(const StockIo *)0);}
uint32_t nds_bulk_44bf0(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_data_expression_data_exp_value_raw(a0,a1,(const StockIo *)0);}
