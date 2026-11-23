#ifndef GP50_COMPONENT_UI_H
#define GP50_COMPONENT_UI_H
#include <stdint.h>
/* Experimental editor-status service v1.
 * An optional manifest callbacks.status callback requests the ordinary editor
 * strip by returning 1..31 printable ASCII bytes. The framework terminates the
 * text; return zero for no request. Capacity includes the framework's final NUL.
 * Do not call GUI functions or retain the borrowed output/context. ABI2 status
 * callbacks share the component's ownership guard with init/tick/GET/SET.
 *
 * Status is best effort: assignment, warnings, GR and capture displays win.
 * Requests are visited in component-id order; the first valid nonempty one wins.
 * It can be omitted or retried, so never advance time or consume an event here.
 * No display is promised outside the ordinary effect editor. Host controls must
 * still expose the same state through the component's GET/SET contract.
 */
#define GP50_COMPONENT_STATUS_CAPACITY 32u
#endif
