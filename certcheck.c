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

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "certcheck.h"
#include "certcheck_version.h"

static FILE *in_qdimacs = NULL;
static FILE *out = NULL;
static PType proof_type = PTYPE_UNDEF;
static unsigned *var_s_levels = NULL;
static int max_var_index = 0;

static void
print_usage (void)
{
  printf ("certcheck [<option>] <qdimacs_file> [<certificate_file>]\n\n");
  printf ("  certcheck merges the input formula with the given");
  printf (" certificate and returns\n  a dimacs file (or optionally an"); 
  printf (" AIGER file).\n\n");
  printf ("  qdimacs_file:\n");
  printf ("    input formula of certificate in QDIMACS format\n\n");
  printf ("  certificate_file:\n");
  printf ("    certificate in AIGER (ascii/binary) format, generated from");
  printf (" qdimacs_file\n");
  printf ("    (stdin if not given)\n\n");
  printf ("  options:\n");
  printf ("    -h, --help      print this message and exit\n");
  printf ("    -a              create AIGER file\n");
  printf ("    --aiger-ascii   write AIG in AIGER ASCII format\n");
  printf ("    --version       print version and exit\n");
}

static void
print_version (void)
{
  printf ("%s\n", CERTCHECK_VERSION);
}

static void
cleanup (void)
{
  if (in_qdimacs != NULL)
    fclose (in_qdimacs);

  if (out != NULL)
    fclose (out);

  if (var_s_levels != NULL)
    free (var_s_levels);
}

int 
main (int argc, char **argv)
{
  int i;
  const char *error;
  char *str, *in_cert_name = NULL, aiger_file = 0, aiger_binary = 1;
  simpleaig *aig = NULL;

  out = stdout;

  for (i = 1; i < argc; i++)
  {
    str = argv[i];

    if (strcmp (str, "-h") == 0 || strcmp (str, "--help") == 0)
    {
      print_usage ();
      return EXIT_SUCCESS;
    }
    else if (strcmp (str, "--version") == 0)
    {
      print_version ();
      return EXIT_SUCCESS;
    }
    else if (strcmp (str, "-a") == 0)
    {
      aiger_file = 1;
    }
    else if (strcmp (str, "--aiger-ascii") == 0)
    {
      aiger_binary = 0;
    }
    else if (str[0] == '-')
    {
      CERTCHECK_ABORT (1, "invalid option '%s'", str);
    }
    else if (in_qdimacs == NULL)
    {
      in_qdimacs = fopen (str, "r");
      CERTCHECK_ABORT (in_qdimacs == NULL, 
                       "failed to open input formula '%s'", str);
    }
    else if (in_cert_name == NULL)
    {
      in_cert_name = str;
    }
  }

  CERTCHECK_ABORT (in_qdimacs == NULL, "no input formula given");

  aig = simpleaig_init ();

  error = simpleaig_read_aiger_from_file (aig, in_cert_name, 0);
  CERTCHECK_ABORT (error, "%s", error);

  aig_add_qdimacs (aig, in_qdimacs);

  if (aiger_file)
    simpleaig_write_aiger_to_file (aig, out, aiger_binary);
  else
    simpleaig_write_cnf_to_file (aig, out);

  simpleaig_reset (aig);
  cleanup ();

  return EXIT_SUCCESS;
}

static void 
aig_add_qdimacs (simpleaig *aig, FILE *in)
{
  assert (aig != NULL);
  assert (in != NULL);

  char c, neg, *is_io;
  int lhs = 0, num, rhs[2];
  unsigned i, num_rhs = 0, num_clauses, s_level = 1;
  Stack clauses, lits, e_vars, u_vars;
  QType scope_type;

  PARSER_SKIP_SPACE_DO_WHILE (c);
  CERTCHECK_ABORT (c == EOF, "empty file given");

  /* skip comments  */
  while (c == QDIMACS_COMMENT)
  {
    while ((c = getc (in)) != '\n' && c != EOF);
    PARSER_SKIP_SPACE_DO_WHILE (c);
  }

  /* preamble  */
  PARSER_SKIP_SPACE_WHILE (c);
  CERTCHECK_ABORT (c != QDIMACS_PREAMBLE, 
                   "invalid char '%c' expected '%c' in preamble", c, 
                   QDIMACS_PREAMBLE);

  PARSER_SKIP_SPACE_DO_WHILE (c);
  CERTCHECK_ABORT (c != QDIMACS_C,
                   "invalid char '%c' expected '%c' in preamble", c, 
                   QDIMACS_PREAMBLE);
  PARSER_SKIP_SPACE_DO_WHILE (c);
  CERTCHECK_ABORT (c != QDIMACS_N,
                   "invalid char '%c' expected '%c' in preamble", c, 
                   QDIMACS_PREAMBLE);
  PARSER_SKIP_SPACE_DO_WHILE (c);
  CERTCHECK_ABORT (c != QDIMACS_F,
                   "invalid char '%c' expected '%c' in preamble", c, 
                   QDIMACS_PREAMBLE);

  PARSER_SKIP_SPACE_DO_WHILE (c);
  PARSER_READ_NUM (max_var_index, c, "number of variables expected");

  PARSER_SKIP_SPACE_DO_WHILE (c);
  PARSER_READ_NUM (num_clauses, c, "number of clauses expected");

  /* scopes  */
  PARSER_SKIP_SPACE_DO_WHILE (c);
  STACK_INIT (e_vars, max_var_index / 2 + 1);
  STACK_INIT (u_vars, max_var_index / 2 + 1);

  var_s_levels = (unsigned *) malloc ((max_var_index + 1) * sizeof (unsigned));
  CERTCHECK_ABORT (var_s_levels == NULL, 
                   "memory allocation failed for var_s_levels");
  memset (var_s_levels, 0, (max_var_index + 1) * sizeof (unsigned));

  while (c == QDIMACS_EXISTS || c == QDIMACS_FORALL)
  {
    scope_type = (c == QDIMACS_EXISTS) ? QTYPE_EXISTS : QTYPE_FORALL;
    PARSER_SKIP_SPACE_DO_WHILE (c);

    while (c != QDIMACS_EOL)
    {
      PARSER_READ_NUM (num, c, "variable expected");

      if (num > max_var_index)
      {
        max_var_index = num;
        var_s_levels = (unsigned *) 
          realloc (var_s_levels, (max_var_index + 1) * sizeof (unsigned)); 
        CERTCHECK_ABORT (var_s_levels == NULL, 
                         "memory reallocation failed for var_s_levels");
      }

      if (scope_type == QTYPE_EXISTS)
        PUSH (e_vars, num);
      else
        PUSH (u_vars, num);

      assert (var_s_levels[num] == 0);
      var_s_levels[num] = s_level;

      /* determine proof type  */
      if (proof_type == PTYPE_UNDEF)
      {
        if (aig->num_inputs > 0 && num == aig->inputs[0])
          proof_type = (scope_type == QTYPE_EXISTS) ? PTYPE_UNSAT : PTYPE_SAT;
        else if (aig->num_outputs > 0 && num == aig->outputs[0])
          proof_type = (scope_type == QTYPE_EXISTS) ? PTYPE_SAT : PTYPE_UNSAT;
        else
          CERTCHECK_ABORT (aig->num_inputs == 0 && aig->num_outputs == 0, 
                           "certificate does not have any inputs/outputs");
      }

      PARSER_SKIP_SPACE_DO_WHILE (c);
    }

    s_level += 1;

    /* skip qdimacs EOL  */
    PARSER_SKIP_SPACE_DO_WHILE (c);
  }
  assert (proof_type != PTYPE_UNDEF);

  /* update lits from certificate AIG to prevent variable index collisions  */
  simpleaig_reencode_aux_ands (aig, max_var_index);

  check_quantifier_levels (aig);

  STACK_INIT (clauses, num_clauses + 1);
  STACK_INIT (lits, 8);

  /* clauses  */
  while (c != EOF)
  {
    while (c != QDIMACS_EOL)
    {
      neg = 0;

      if (c == MINUS)
      {
        neg = 1;
        PARSER_SKIP_SPACE_DO_WHILE (c);
      }

      PARSER_READ_NUM (num, c, "literal expected");

      if (neg)
        num = -num;

      PUSH (lits, num);
      PARSER_SKIP_SPACE_DO_WHILE (c);
    }

    PUSH (clauses, aig_add_clause (aig, lits.bp, STACK_CNT (lits)));
    STACK_RESET (lits);

    PARSER_SKIP_SPACE_DO_WHILE (c);
  }

  CERTCHECK_ABORT (STACK_CNT (clauses) == 0, "empty input formula given");

  /* conjunction of all clauses  */
  for (i = 0; i < (unsigned) STACK_CNT (clauses); i++)
  {
    lhs = clauses.bp[i];
    rhs[num_rhs++] = lhs;

    if (num_rhs == 2)
    {
      lhs = simpleaig_add_and (aig, SIMPLEAIG_FALSE, rhs[0], rhs[1]); 

      rhs[0] = lhs;
      num_rhs = 1;
    }
  }

  is_io = (char *) malloc ((aig->max_var + 1) * sizeof (char));
  assert (is_io != NULL);
  memset (is_io, 0, (aig->max_var + 1) * sizeof (char));

  for (i = 0; i < aig->num_inputs; i++)
    is_io[aig->inputs[i]] = 1;

  for (i = 0; i < aig->num_outputs; i++)
    is_io[abs (aig->outputs[i])] = 1;

  /* reset outputs from certificate  */
  aig->num_outputs = 0;
  
  /* negate output in case of a sat proof and add resp. input variables  */
  if (proof_type == PTYPE_SAT)
    lhs = simpleaig_not (lhs);
  
  /* add all remaining inputs or don't care outputs  */
  for (i = 0; i < (unsigned) STACK_CNT (u_vars); i++)
    if (!is_io[u_vars.bp[i]])
      simpleaig_add_input (aig, u_vars.bp[i]);

  for (i = 0; i < (unsigned) STACK_CNT (e_vars); i++)
    if (!is_io[e_vars.bp[i]])
      simpleaig_add_input (aig, e_vars.bp[i]);

  simpleaig_add_output (aig, lhs);
  assert (aig->num_outputs == 1);

  STACK_FREE (e_vars);
  STACK_FREE (u_vars);
  STACK_FREE (lits);
  STACK_FREE (clauses);
}

static int
aig_add_clause (simpleaig *aig, int *lits, unsigned num_lits)
{
  assert (aig != NULL);
  assert (lits != NULL);
  assert (num_lits > 0);

  int lhs = 0, rhs[2];
  unsigned i, num_rhs = 0;

  /* construct AIG from clause, negate literals  */
  for (i = 0; i < num_lits; i++)
  {
    lhs = simpleaig_not (lits[i]);
    rhs[num_rhs++] = lhs;

    if (num_rhs == 2)
    {
      lhs = simpleaig_add_and (aig, SIMPLEAIG_FALSE, rhs[0], rhs[1]); 

      rhs[0] = lhs;
      num_rhs = 1;
    }
  }

  return simpleaig_not (lhs);
}

static void
check_quantifier_levels (simpleaig *aig)
{
  int i, *and_map, lhs, rhs0, rhs1, var;
  Stack visit;

  assert (aig != NULL);

  and_map = (int *) malloc ((aig->lhs_aux + 1) * sizeof (int));
  memset (and_map, -1, (aig->lhs_aux + 1) * sizeof (int));

  /* map lhs to index in aig->ands  */
  for (i = 0; (unsigned) i < aig->num_ands; i++)
    and_map[aig->ands[i].lhs] = i;

  STACK_INIT (visit, 8);

  for (i = 0; (unsigned) i < aig->num_outputs; i++)
  {
    var = aig->outputs[i];

    if (and_map[var] < 0)
      continue;
    if (var_s_levels[var] <= 0)
      continue; 

    PUSH (visit, var);

    while (!STACK_IS_EMPTY (visit))
    {
      POP (visit, lhs);

      if (and_map[lhs] < 0)
        continue;

      rhs0 = (aig->ands[and_map[lhs]]).rhs0;
      rhs1 = (aig->ands[and_map[lhs]]).rhs1;

      CERTCHECK_ABORT (IS_VAR (rhs0) && QLEVEL (rhs0) > QLEVEL (var),
        "function of variable %d (level %d) depends on variable %d "
        "(level %d) with higher quantification level\n",
        var, var_s_levels[var], abs (rhs0), var_s_levels[abs (rhs0)]);

      CERTCHECK_ABORT (IS_VAR (rhs1) && QLEVEL (rhs1) > QLEVEL (var),
        "function of variable %d (level %d) depends on variable %d "
        "(level %d) with higher quantification level\n",
        var, var_s_levels[var], abs (rhs1), var_s_levels[abs (rhs1)]);

      if (rhs0 != SIMPLEAIG_TRUE && rhs0 != SIMPLEAIG_FALSE &&
          and_map[abs (rhs0)] >= 0 && abs (rhs0) > max_var_index)
      {
        PUSH (visit, abs (rhs0));
      }

      if (rhs1 != SIMPLEAIG_TRUE && rhs1 != SIMPLEAIG_FALSE &&
          and_map[abs (rhs1)] >= 0 && abs (rhs1) > max_var_index)
      {
        PUSH (visit, abs (rhs1));
      }
    }
  }

  STACK_FREE (visit);
  free (and_map);
}
