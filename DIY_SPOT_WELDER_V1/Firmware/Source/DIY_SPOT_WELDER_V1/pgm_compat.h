// SPDX-License-Identifier: GPL-3.0-or-later
// Flash-string helpers that also compile on the host (tests).
#pragma once
#ifdef __AVR__
#include <avr/pgmspace.h>
#else
#include <string.h>
#ifndef PROGMEM
#define PROGMEM
#endif
#ifndef PSTR
#define PSTR(s) (s)
#endif
#define pgm_read_ptr(p) (*(p))
#define strcpy_P strcpy
#endif
