/*  CertCheck: Tool for merging QBF formula with its corresponding certificate. 
 *
 *  Copyright (c) 2011-2012 Mathias Preiner.
 *
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *  
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *  
 *  You should have received a copy of the GNU General Public License
 *  along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef INCLUDE_CERTCHECK_H
#define INCLUDE_CERTCHECK_H

#include <ctype.h>
#include "simpleaig.h"

#define CERTCHECK_ABORT(cond, msg, ...)                      \
  do                                                         \
  {                                                          \
    if (cond)                                                \
    {                                                        \
      fprintf (stderr, "[CERTCHECK] %s: ", __func__);        \
      fprintf (stderr, msg, ## __VA_ARGS__);                 \
      fprintf (stderr, "\n");                                \
      cleanup ();                                            \
      abort ();                                              \
    }                                                        \
  }                                                          \
  while (0)

#define PARSER_SKIP_SPACE_DO_WHILE(c) \
  do                                  \
  {                                   \
    c = getc (in);                    \
  }                                   \
  while (isspace (c));
  
#define PARSER_SKIP_SPACE_WHILE(c)    \
  while (isspace (c)) c = getc (in);

#define PARSER_READ_NUM(num, c, msg) \
  do                                 \
  {                                  \
    num = 0;                         \
    for (;;)                         \
    {                                \
      if (!isdigit (c))              \
        CERTCHECK_ABORT (1, msg);    \
      num = num * 10 + (c - '0');    \
      if (isspace (c = getc (in)))   \
        break;                       \
    }                                \
  }                                  \
  while (0)

#define STACK_INIT(stack, stack_size)                               \
  do                                                                \
  {                                                                 \
    stack.bp = (int *) malloc ((stack_size) * sizeof (int));        \
    CERTCHECK_ABORT (stack.bp == NULL, "memory allocation failed"); \
    memset (stack.bp, 0, (stack_size) * sizeof (int));              \
    stack.sp = stack.bp;                                            \
    stack.size = stack_size;                                        \
  }                                                                 \
  while (0)

#define STACK_FREE(stack) \
  free (stack.bp);

#define STACK_IS_EMPTY(stack) \
  (stack.bp == stack.sp)

#define STACK_RESET(stack) \
  (stack.sp = stack.bp)

#define STACK_CNT(stack) \
  (stack.sp - stack.bp)

#define PUSH(stack, num)                                                \
  do                                                                    \
  {                                                                     \
    *(stack.sp) = num;                                                  \
    stack.sp += 1;                                                      \
    if (stack.sp - stack.bp >= stack.size)                              \
    {                                                                   \
      stack.size <<= 1;                                                 \
      stack.bp = (int *) realloc (stack.bp, stack.size * sizeof (int)); \
      CERTCHECK_ABORT (stack.bp == NULL, "memory reallocation failed");   \
      stack.sp = stack.bp + (stack.size >> 1 );                         \
    }                                                                   \
  }                                                                     \
  while (0)

#define POP(stack, num) \
  do                    \
  {                     \
    stack.sp -= 1;      \
    num = *(stack.sp);  \
    *(stack.sp) = 0;    \
  }                     \
  while(0)

#define IS_VAR(num)\
  (num != SIMPLEAIG_TRUE && num != SIMPLEAIG_FALSE && \
   abs (num) > 0 && abs (num) <= max_var_index)

#define QLEVEL(var)\
  (var_s_levels[abs (var)])

#define QDIMACS_COMMENT 'c'
#define QDIMACS_PREAMBLE 'p'
#define QDIMACS_C 'c'
#define QDIMACS_N 'n'
#define QDIMACS_F 'f'
#define QDIMACS_EOL '0'
#define QDIMACS_FORALL 'a'
#define QDIMACS_EXISTS 'e'
#define MINUS '-'

typedef struct
{
  int size;
  int *bp;
  int *sp;
} Stack;

typedef enum
{
  PTYPE_UNDEF,
  PTYPE_SAT,
  PTYPE_UNSAT
} PType;

typedef enum
{
  QTYPE_EXISTS,
  QTYPE_FORALL
} QType;

static void aig_add_qdimacs (simpleaig *, FILE *);
static int aig_add_clause (simpleaig *, int *, unsigned);
static void check_quantifier_levels (simpleaig *);

#endif
