#ifndef GP50_ASSIGNMENT_MENU_H
#define GP50_ASSIGNMENT_MENU_H
#include "assign_editor.h"
enum { ASSIGN_MENU=20, ASSIGN_PICK=21, ASSIGN_CONFIRM=22, ASSIGN_EMPTY=23,
       ASSIGN_DONE=24, ASSIGN_RECOVER=25, ASSIGN_CHANGED=26 };
uint32_t assignment_input(uint32_t ctx,uint32_t event,const StockIo *io);
uint32_t assignment_tick(uint32_t ctx,const StockIo *io);
#endif
