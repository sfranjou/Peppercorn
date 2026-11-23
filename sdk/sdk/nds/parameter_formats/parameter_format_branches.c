/* Stock incoming float ABI; local compared bodies inline into public adapters. */
#define GP50_CATALOG_DIRECT 1
#define GP50_FORMAT_LOCAL static inline __attribute__((always_inline))
#define parameter_branch_19050 owned_parameter_branch_19050
#define parameter_branch_19086 owned_parameter_branch_19086
#define parameter_branch_1910c owned_parameter_branch_1910c
#define parameter_branch_19140 owned_parameter_branch_19140
#define parameter_branch_191a0 owned_parameter_branch_191a0
#define parameter_branch_191f6 owned_parameter_branch_191f6
#define parameter_branch_1922e owned_parameter_branch_1922e
#define parameter_branch_193b6 owned_parameter_branch_193b6
#define parameter_branch_193ea owned_parameter_branch_193ea
#define parameter_branch_1940a owned_parameter_branch_1940a
#define parameter_branch_1943a owned_parameter_branch_1943a
#define parameter_branch_19472 owned_parameter_branch_19472
#define parameter_branch_19522 owned_parameter_branch_19522
#define parameter_branch_19566 owned_parameter_branch_19566
#define parameter_branch_195d6 owned_parameter_branch_195d6
#define parameter_branch_19638 owned_parameter_branch_19638
#define parameter_format_dispatch owned_parameter_format_dispatch
#define parameter_format_ten owned_parameter_format_ten
#define parameter_format_zero owned_parameter_format_zero
#include "../../../firmware/reconstructed/nds/parameter_format_branches.c"
void nds_pfmt_19050(uint32_t out,uint32_t length,float value) { union {float f;uint32_t u;} v={.f=value};owned_parameter_branch_19050(out,length,v.u,0); }
void nds_pfmt_19086(uint32_t out,uint32_t length,float value) { union {float f;uint32_t u;} v={.f=value};owned_parameter_branch_19086(out,length,v.u,0); }
void nds_pfmt_1910c(uint32_t out,uint32_t length,float value) { union {float f;uint32_t u;} v={.f=value};owned_parameter_branch_1910c(out,length,v.u,0); }
void nds_pfmt_19140(uint32_t out,uint32_t length,float value) { union {float f;uint32_t u;} v={.f=value};owned_parameter_branch_19140(out,length,v.u,0); }
void nds_pfmt_191a0(uint32_t out,uint32_t length,float value) { union {float f;uint32_t u;} v={.f=value};owned_parameter_branch_191a0(out,length,v.u,0); }
void nds_pfmt_191f6(uint32_t out,uint32_t length,float value) { union {float f;uint32_t u;} v={.f=value};owned_parameter_branch_191f6(out,length,v.u,0); }
void nds_pfmt_1922e(uint32_t out,uint32_t length,float value) { union {float f;uint32_t u;} v={.f=value};owned_parameter_branch_1922e(out,length,v.u,0); }
void nds_pfmt_193b6(uint32_t out,uint32_t length,float value) { union {float f;uint32_t u;} v={.f=value};owned_parameter_branch_193b6(out,length,v.u,0); }
void nds_pfmt_193ea(uint32_t out,uint32_t length,float value) { union {float f;uint32_t u;} v={.f=value};owned_parameter_branch_193ea(out,length,v.u,0); }
void nds_pfmt_1940a(uint32_t out,uint32_t length,float value) { union {float f;uint32_t u;} v={.f=value};owned_parameter_branch_1940a(out,length,v.u,0); }
void nds_pfmt_1943a(uint32_t out,uint32_t length,float value) { union {float f;uint32_t u;} v={.f=value};owned_parameter_branch_1943a(out,length,v.u,0); }
void nds_pfmt_19472(uint32_t out,uint32_t length,float value) { union {float f;uint32_t u;} v={.f=value};owned_parameter_branch_19472(out,length,v.u,0); }
void nds_pfmt_19522(uint32_t out,uint32_t length,float value) { union {float f;uint32_t u;} v={.f=value};owned_parameter_branch_19522(out,length,v.u,0); }
void nds_pfmt_19566(uint32_t out,uint32_t length,float value) { union {float f;uint32_t u;} v={.f=value};owned_parameter_branch_19566(out,length,v.u,0); }
void nds_pfmt_195d6(uint32_t out,uint32_t length,float value) { union {float f;uint32_t u;} v={.f=value};owned_parameter_branch_195d6(out,length,v.u,0); }
void nds_pfmt_19638(uint32_t out,uint32_t length,float value) { union {float f;uint32_t u;} v={.f=value};owned_parameter_branch_19638(out,length,v.u,0); }
void nds_pfmt_1961c(uint32_t out,uint32_t length,uint32_t index,float value) { union {float f;uint32_t u;} v={.f=value};owned_parameter_format_dispatch(out,length,index,v.u,0); }
uint32_t nds_pfmt_19662(void) { return owned_parameter_format_ten(0); }
uint32_t nds_pfmt_19666(void) { return owned_parameter_format_zero(0); }
