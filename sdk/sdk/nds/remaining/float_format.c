/* Real hard-float/variadic adapter for 18f0a. Preserve stock numeric services;
 * reject overflowing expanded formats and nonrepresentable integer inputs. */
#include <stdint.h>
typedef int (*format_fn)(char *, uint32_t, const char *, ...);
typedef double (*unsigned_double_fn)(uint32_t);
typedef double (*signed_double_fn)(int32_t);
typedef double (*float_double_fn)(float);
typedef double (*binary_double_fn)(double, double);
typedef uint32_t (*double_word_fn)(double);
#define AT(type, a) ((type)(uintptr_t)(a))
uint32_t nds_remaining_18f0a(uint32_t destination, uint32_t limit,
                           const char *text, float value) {
    char buffer[108];
    uint32_t index = 0, precision = 0, conversions = 0;
    /* C's float-to-integer cast is undefined outside this domain. */
    if (!(value >= -2147483648.0f && value < 2147483648.0f)) goto invalid;
    while (*text) {
        if (text[0] == '%' && text[1] == '%') {
            if (index + 2 >= sizeof buffer) goto invalid;
            buffer[index++] = '%'; buffer[index++] = '%'; text += 2;
        } else if (text[0] == '%' && text[1] == 'd') {
            if (conversions++ || index + 2 >= sizeof buffer) goto invalid;
            buffer[index++] = '%'; buffer[index++] = 'd'; text += 2;
        } else if (text[0] == '%' && text[1] == '.' && text[2] && text[3] == 'f') {
            if (conversions++) goto invalid;
            uint8_t digit = (uint8_t)text[2];
            if (digit < '0' || digit > '9') goto invalid;
            uint32_t length = digit == '0' ? 2u : 7u;
            if (index + length >= sizeof buffer) goto invalid;
            buffer[index++] = '%'; buffer[index++] = 'd';
            if (digit != '0') {
                buffer[index++] = '.'; buffer[index++] = '%';
                buffer[index++] = '0'; buffer[index++] = (char)digit;
                buffer[index++] = 'd';
            }
            precision = (uint8_t)(digit - '0'); text += 4;
        } else {
            if (*text == '%') goto invalid;
            if (index + 1 >= sizeof buffer) goto invalid;
            buffer[index++] = *text++;
        }
    }
    buffer[index] = 0;
    int32_t integer = (int32_t)value;
    if (!precision)
        return AT(format_fn, 0xd0d3c)((char *)(uintptr_t)destination, limit, buffer, integer);
    float adjusted = value + *(const volatile float *)0xd4ed4;
    if (!(adjusted >= -2147483648.0f && adjusted < 2147483648.0f)) goto invalid;
    double exponent = AT(unsigned_double_fn, 0xd08a2)(precision);
    double scale = AT(binary_double_fn, 0xcc8ba)(*(const volatile double *)0xd4ee8, exponent);
    double fraction_input = AT(float_double_fn, 0xd08fc)(adjusted);
    double product = AT(binary_double_fn, 0xcfe98)(fraction_input, scale);
    double integral = AT(signed_double_fn, 0xd0838)((int32_t)adjusted);
    double integral_product = AT(binary_double_fn, 0xcfe98)(integral, scale);
    double difference = AT(binary_double_fn, 0xd0288)(product, integral_product);
    uint32_t fraction = AT(double_word_fn, 0xcf12c)(difference);
    return AT(format_fn, 0xd0d3c)((char *)(uintptr_t)destination, limit, buffer, integer, fraction);
invalid:
    if (limit) *(volatile char *)(uintptr_t)destination = 0;
    return 0;
}
