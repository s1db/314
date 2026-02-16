# 314: A Data-Driven QBF/DQBF Solver

314 is a hackable and extensible QBF/DQBF solver that uses data-driven techniques to solve QBF/DQBF problems. It is inspired by Manthan and allows for easy experimentation with new techniques.

## Directory Structure

The project is organized into the following modules:

1. `src/solver.py`: The main solver logic.
2. `src/instance_parsers/`: Parses the input QBF/DQBF instance and stores it in a canonical format.
   - `qbf.py`: Parses QBF instances.
   - `dqbf.py`: Parses DQBF instances.
3. `src/sampling_schemes/`: Samples assignments for the existential variables.
   - `uniform.py`: Samples assignments uniformly.
4. `src/preprocessors/`: Preprocesses the instance to make it easier to solve.
5. `src/dependency_schemes/`: Computes dependency schemes for the instance.
6. `src/function_approximators/`: Approximates the functions to be computed.
7. `src/checkers/`: Checks if the functions are correct.
8. `src/repair_schemes/`: Repairs the functions if they are incorrect.
9. `src/solution_emitters/`: Emits the solution to the instance.
10. `src/function.py`: Class definition for functions.

## Theoretical Background of Manthan (Boolean Functional Synthesis)

### Problem Statement

Given an existentially quantified Boolean formula $\exists Y F(X,Y)$ over the set of variables $X$ and $Y$, the problem of Boolean functional synthesis is to compute a vector of Boolean functions, denoted by $\Psi(X)=\langle\psi_{1}(X),\psi_{2}(X),...,\psi_{|Y|}(X)\rangle$ (referred to as the _Skolem function vector_), such that:

$$ \exists Y F(X,Y) \equiv F(X, \Psi(X)) $$

In the context of applications:
- The sets $X$ and $Y$ are viewed as inputs and outputs, respectively.
- The formula $F(X,Y)$ is viewed as a functional specification capturing the relationship between $X$ and $Y$.
- The Skolem function vector $\Psi(X)$ allows one to determine the value of $Y$ for a given $X$ by evaluating $\Psi$.

The study of Boolean functional synthesis traces back to Boole [12]. Over the decades, the problem has found applications in a wide variety of domains such as certified QBF solving [8, 9, 35, 40], automated program repair [26], program synthesis [43], and cryptography [34].

### Approach: Manthan (Boolean Functional Synthesis)

We take a step towards solving this by adopting the approach of **Manthan**, which sits at the intersection of machine learning, constrained sampling, and automated reasoning. We view the problem of Boolean functional synthesis through the lens of multi-class classification aided by the generation of data via constrained sampling, and employ automated reasoning to certify and refine the learned functions.

The architecture comprises three novel techniques:

1.  **Data Generation**: A weighted sampling strategy generates a representative dataset that seeks to uniformly sample input variables ($X$) while biasing the valuations of output variables towards a particular value.
2.  **Dependency-Driven Classifier for Candidates**: A dependency-aware classifier constructs a vector of decision trees corresponding to each $y_i$, wherein each decision tree is expressed as a Boolean function.
3.  **Proof-Guided Refinement**: A proof-guided refinement approach seeks to identify and apply minor repairs to the candidate functions iteratively until convergence to a provably correct Skolem function vector. It uses a MaxSAT solver to determine potential repair candidates and employs unsatisfiability cores obtained from infeasibility proofs.

### Error Formula

We refer to $E(X,Y,Y')$ as an error formula where $Y'=\{y'_{1},...,y'_{|Y|}\}$ and $Y' \neq Y$:

$$ E(X,Y,Y') = F(X,Y) \wedge \neg F(X,Y') \wedge (Y' \leftrightarrow \Psi) $$

**Theorem 1 [27]**: $\Psi$ is a Skolem function if and only if $E(X,Y,Y')$ is UNSAT.

## Dependency Management of Manthan

Manthan handles dependencies dynamically using a Directed Acyclic Graph (DAG), referred to in the code as `dg` (Dependency Graph). Unlike traditional approaches that might fix an order statically based on the input formula (like QBF prenex normal form), Manthan discovers dependencies via machine learning and enforces them strictly during the repair loop to ensure the final circuit is combinational (acyclic).

### 1. The Dependency Graph Object (`dg`)

- **Implementation**: `networkx.DiGraph`
- **Nodes**: Represent existentially quantified variables ($Y$).
- **Edges**: A directed edge $y_i \to y_j$ signifies "$y_i$ depends on $y_j$".
- **Semantic**: To compute the value of $y_i$, the circuit can read the value of $y_j$.
- **Ordering Consequence**: In a topological sort, $y_i$ will appear before $y_j$.

### 2. Phase I: Initialization & DQBF Handling

In `src/preprocess.py`, the graph is initialized.

- **Standard QBF**: The graph starts with nodes but no edges. The dependencies are initially unknown and will be learned.
- **DQBF (Henkin Quantifiers)**: Manthan explicitly calculates allowed dependencies based on the quantifier structure.
    - **Logic**: If the set of input variables ($X$) that $y_j$ depends on is a subset of the inputs $y_i$ depends on, then $y_j$ is "more fundamental" than $y_i$.
    - **Code**: `dg.add_edge(yvar_i, yvar_j)` is executed if `HenkinDep[yvar_j].issubset(HenkinDep[yvar_i])`.
    - **Result**: This pre-populates the graph with "hard" structural dependencies that cannot be violated.

### 3. Phase II: Discovery via Decision Trees

The primary source of dependencies in Manthan is the Candidate Learning phase (`src/candidateSkolem.py`).

- **The Process**: Manthan learns a decision tree to predict the value of $y_i$. The features used in this tree can be input variables ($X$) or other output variables ($Y$).
- **Feature Extraction**: The function `treepaths` traverses the learned decision tree. If a split node uses a variable `data_feature_names[feature[root]]` that belongs to $Y$ (let's call it $y_{feat}$), it is recorded as a dependency.
- **Graph Update**: For every $Y$ variable found in the tree for $y_i$, an edge is added: `dg.add_edge(y_i, y_{feat})`.
    - **Code**: `dg.add_edge(var, jvar)` where `var` is the function being learned and `jvar` is the feature used.

### 4. Phase III: The Global Ordering (TotalOrder)

Once learning is complete, Manthan linearizes the graph to establish a safe repair order.

- **Computation**: `YvarOrder = np.array(list(nx.topological_sort(dg)))` in `manthan.py`.
- **The Structure of the List**: Because edges go $Dependent \to Independent$, the topological sort produces a list in Reverse Computation Order.
    - `YvarOrder = [y_dependent, ..., y_independent]`
- **Example**: If $y_1$ uses $y_2$, the edge is $y_1 \to y_2$. The list is `[y_1, y_2]`.

### 5. Phase IV: Enforcing Acyclicity in Repair

The most critical usage of this dependency structure is in `src/repair.py`. When repairing a function, Manthan must ensure it doesn't introduce a cycle (e.g., making $y_2$ depend back on $y_1$).

- **Allowed Dependencies (`allowed_Y`)**:
    When repairing `repairvar` (say $y_i$), Manthan finds its index in `YvarOrder`.
    
    ```python
    repairvar_index = np.where(YvarOrder == repairvar)[0][0]
    allowed_Y = YvarOrder[repairvar_index:] # Slicing the suffix
    ```

- **Mechanism**: Since the list is `[Dependent ... Independent]`, variables appearing after $y_i$ are "more independent" (upstream). Variables appearing before $y_i$ are downstream (dependent on $y_i$).
- **The Constraint**: The repair patch is strictly forbidden from using any variable not in this `allowed_Y` suffix. This guarantees that $y_i$ only "looks down" the chain, preventing cycles.

### 6. Manthan2 Feature: Clustering with Primal Graphs

Manthan2 introduces a separate dependency concept for Multi-Classification (`src/convertVerilog.py` and `src/candidateSkolem.py`).

- **The Primal Graph (`ng`)**:
    - **Nodes**: $Y$ variables.
    - **Edges**: Added between $y_i$ and $y_j$ if they appear in the same CNF clause.
- **Purpose**: This graph measures "cohesion" or "relatedness," not functional dependency.
- **Usage**: `createCluster` uses this graph to group related variables (e.g., variables distance $k$ apart). These clusters are learned together in a single multi-class decision tree.
- **Dependency implication**: Variables in the same cluster are predicted jointly, so they do not depend on each other functionally (they are siblings), but they likely depend on the same set of upstream variables.

### Summary Flow Example

1. **Parse**: $y_1, y_2$ exist.
2. **Learn**: Tree for $y_1$ splits on $y_2$.
3. **Update Graph**: Add edge $y_1 \to y_2$ ("$y_1$ needs $y_2$").
4. **Sort**: `TotalOrder` becomes `[y_1, y_2]`.
5. **Repair $y_1$**: Can use `{y_1, y_2}` (allows self-reference for bit-flipping, and $y_2$).
6. **Repair $y_2$**: Can use `{y_2}`. Cannot use $y_1$ (because $y_1$ is before $y_2$ in the list).

## Algorithms

### Main Algorithm: Manthan

**Algorithm 1: Manthan $(F(X,Y))$**

```
Running Manthan(F(X,Y)):
  Ψ, U ← Preprocess(F(X,Y))
  Σ ← GetSamples(F(X,Y))
  D ← ∅
  foreach y_j in Y \ U do:
      ψ_j, D ← CandidateSkF(Σ, F(X,Y), y_j, D)
  
  TotalOrder ← FindOrder(D)
  
  repeat:
      E(X,Y,Y') ← F(X,Y) ∧ ¬F(X,Y') ∧ (Y' ↔ Ψ)
      ret, σ ← CheckSat(E(X,Y,Y'))
      if ret == SAT then:
          Ψ ← RefineSkF(F(X,Y), Ψ, σ, TotalOrder)
  until ret == UNSAT
  
  Substitute(F(X,Y), Ψ, TotalOrder)
  return Ψ
```

### Preprocessing

**Algorithm 2: Preprocess $(F(X,Y))$**

```
Preprocess(F(X,Y)):
  U ← ∅
  foreach y_j in Y do:
      # Check for constant positive
      ret_pos, ρ_pos ← CheckSat(F(X,Y)|_{y_j=0} ∧ ¬F(X,Y)|_{y_j=1})
      if ret_pos == UNSAT then:
          U ← U ∪ {y_j}
          F(X,Y) ← F(X,Y)|_{y_j=1}
          ψ_j ← 1
      else:
          # Check for constant negative
          ret_neg, ρ_neg ← CheckSat(F(X,Y)|_{y_j=1} ∧ ¬F(X,Y)|_{y_j=0})
          if ret_neg == UNSAT then:
              U ← U ∪ {y_j}
              F(X,Y) ← F(X,Y)|_{y_j=0}
              ψ_j ← 0
  return Ψ, U
```

### Sampling Strategy

**Algorithm 3: GetSamples $(F(X,Y))$**

```
GetSamples(F(X,Y)):
  Σ_1 ← AdaBiasGen(F(X,Y), 500, 0.5, 0.9)
  Σ_2 ← AdaBiasGen(F(X,Y), 500, 0.5, 0.1)
  
  foreach y_j in Y do:
      m_j ← Count(Σ_1 ∩ (y_j=1)) / 500
      n_j ← Count(Σ_1 ∩ (y_j=0)) / 500
      if (0.35 < m_j < 0.65) ∧ (0.35 < n_j < 0.65) then:
          q_j ← m_j
      else:
          q_j ← 0.9
          
  Σ ← AdaBiasGen(F(X,Y), 0.5, q)
  return Σ
```

### Candidate Generation (Decision Tree)

We use the ID3 algorithm [37] to construct a decision tree $t$ using the Gini Index as the measure of impurity.

**Algorithm 4: CandidateSkF $(\Sigma, F(X, Y), y_j, D)$**

```
CandidateSkF(Σ, F(X,Y), y_j, D):
  featset ← X
  foreach y_k in Y \ {y_j} do:
      if y_j not in d_k then:
          featset ← featset ∪ {y_k}  /* include if y_k is not dependent on y_j */
          
  feat, lbl ← Σ↓featset, Σ↓y_j
  t ← CreateDecisionTree(feat, lbl)
  
  foreach n in LeafNodes(t) do:
      if Label(n) == 1 then:
          π ← Path(t, root, n)
          ψ_j ← ψ_j ∨ π
          
  foreach y_k in ψ_j do:
      d_j ← d_j ∪ {y_k} ∪ d_k
      
  return ψ_j, D
```

### Refinement

**Algorithm 5: RefineSkF $(F(X,Y), \Psi, \sigma, TotalOrder)$**

```
RefineSkF(F(X,Y), Ψ, σ, TotalOrder):
  H ← F(X,Y) ∧ (X ↔ σ[X])
  S ← (Y ↔ σ[Y'])
  Ind ← MaxSATList(H, S)
  
  foreach y_k in Ind do:
      Ŷ = {TotalOrder[index(y_k) + 1], ..., TotalOrder[|Y|]}
      if CheckSubstitute(y_k) then:
          DoSelfSubstitution(F(X,Y), y_k, Y \ Ŷ)
      else:
          G_k ← (y_k ↔ σ[y_k']) ∧ F(X,Y) ∧ (X ↔ σ[X]) ∧ (Ŷ ↔ σ[Ŷ])
          ret, ρ ← CheckSat(G_k)
          if ret == UNSAT then:
              C ← FindCore(G_k)
              β ← ⋀ ite((σ[l]=1), l, ¬l) for l in C
              ψ_k ← ite((σ[y_k'] == 1), ψ_k ∧ ¬β, ψ_k ∨ β)
          else:
              foreach y_t in Y \ Ŷ do:
                  if ρ[y_t] ≠ σ[y_t'] then:
                      Ind.Append(y_t)
              σ[y_k] ← σ[y_k']
  return Ψ
```

## Manthan's Error Formula Construction

### 1. The Mathematical Objective

Manthan verifies its learned candidate functions by constructing an Error Formula $E(X, Y, Y')$. If this formula is Satisfiable (SAT), it means there exists an input $X$ where the functions fail.

$$ E(X, Y, Y') = \underbrace{F(X, Y)}_{\text{Spec is satisfiable}} \land \underbrace{(Y' \leftrightarrow \Psi(X))}_{\text{Candidates generated } Y'} \land \underbrace{\neg F(X, Y')}_{\text{Generated } Y' \text{ is invalid}} $$

### 2. Implementation Strategy: Structural Verilog

Manthan does not build this formula using CNF clauses directly. Instead, it generates a Verilog module (`MAIN`) that structurally wires together the original specification and the candidate functions. This takes advantage of the ABC tool's ability to synthesize and check Verilog designs.

The implementation is located in the function `createErrorFormula` in `src/createSkolem.py`.

### 3. Detailed Construction Steps

#### A. Module Definition & Inputs
The system creates a top-level module named `MAIN`. It takes three sets of inputs:
- **$X$ Variables**: The original inputs (e.g., 1, 2, 3).
- **$Y$ Variables**: A valid solution oracle (e.g., 4, 5).
- **$Y'$ Variables**: The values predicted by the candidate functions (named ip4, ip5).

```python
# src/createSkolem.py
inputformula = '('       # Inputs for F(X, Y)
inputskolem = '('        # Inputs for Skolem Check (X, Y')
inputerrorx = 'module MAIN (' # Top level module definition
# ... loops to populate lists ...
```

#### B. The Three Logical Components
The module instantiates three sub-components to compute the necessary boolean conditions.

**Component 1: The Existence Check ($F(X, Y)$)**
- **Purpose**: Ensures we only look for errors on inputs $X$ where a solution is actually possible.
- **Implementation**: Instantiates the original formula `FORMULA` as instance `F1`.
- **Wiring**: Connects $X$ and $Y$.
- **Output**: `out1`.
- **Code**: `FORMULA F1 (..., out1 );`

**Component 2: The Candidate Consistency Check ($Y' \leftrightarrow \Psi(X)$)**
- **Purpose**: Ensures the variables $Y'$ actually match what the current candidate functions $\Psi$ would produce for input $X$.
- **Implementation**: Instantiates `SKOLEMFORMULA` (created by `createSkolem` function) as instance `F2`.
- **Wiring**: Connects $X$ and $Y'$ (passed as ip variables).
- **Output**: `out2`.
- **Code**: `SKOLEMFORMULA F2 (..., out2 );`

> **Deep Dive on `SKOLEMFORMULA`**:
> Unlike a standard function that returns a value, this module verifies values.
> Inside `createSkolem`, it generates logic like `(~(w_var ^ o_var))`. This is an XNOR gate (Equality check) between the computed wire `w_var` (the decision tree output) and the input `o_var` ($Y'$).
> It ANDs all these checks together. `out2` is High only if all $Y'$ variables match the function predictions.

**Component 3: The Failure Check ($\neg F(X, Y')$)**
- **Purpose**: Checks if the candidate outputs $Y'$ violate the specification.
- **Implementation**: Instantiates the original formula `FORMULA` again as instance `F2` (note: reuse of module name `FORMULA`, but distinct instance).
- **Wiring**: Connects $X$ and $Y'$.
- **Output**: `out3`.
- **Code**: `FORMULA F2 (..., out3 );`

#### C. The Final Wiring
The function combines these three signals into a single output `out` using a continuous assignment.

```python
# src/createSkolem.py
error_content += "assign out = ( out1 & out2 & ~(out3) );\n"
```

- `out1`: The input is valid ($F(X, Y)$ is True).
- `out2`: $Y'$ matches the function output ($Y' = \Psi(X)$).
- `~out3`: The function output is WRONG ($F(X, Y')$ is False).

### 4. Code Flow Summary
1.  **Generate `SKOLEMFORMULA`**: First, `createSkolem` writes a Verilog file defining the logic of the decision trees and the equality checks.
2.  **Generate `MAIN`**: `createErrorFormula` writes the wiring logic described above.
3.  **Combine**: `addSkolem` concatenates the `MAIN` module, the `SKOLEMFORMULA` module, and the original `FORMULA` (passed as `verilog_formula`) into a single file `_errorformula.v`.
4.  **Verify**: This file is passed to an external verification tool (ABC via `file_generation_cex`) to check for satisfiability.

### 5. Why this implementation?
By constructing the error formula in Verilog rather than raw CNF, Manthan preserves the high-level structure of the circuit. This allows the backend ABC solver to apply structural reductions (like sweeping and rewriting) before blasting it to CNF for the final SAT check, which is generally more efficient than operating on a raw CNF expansion of the entire error condition.

## Engineering for the Parser: Manthan's Hierarchical Verilog Generation

Manthan ensures its generated Verilog is parsable by even the most primitive tools by avoiding behavioral logic (always blocks) and, crucially, by batching large boolean operations into intermediate wires. This effectively builds a "tree of gates" rather than one massive gate.

### 1. Clause Aggregation (The "100-Batch" Rule)
**Source**: `src/convertVerilog.py`

When converting the original CNF (QDIMACS) into the `FORMULA` module, Manthan has to AND together potentially millions of clauses.

- **Naive Approach (Fails)**: `assign out = (c1 & c2 & ... & c1000000);`
- **Manthan's Approach**: It introduces two layers of intermediate wires: `t_` (Clause Wires) and `tcount_` (Batch Wires).

**Step A: Individual Clause Wires (`t_i`)**
Every single clause in the CNF is assigned its own wire.

```verilog
wire t_1;
assign t_1 = 1 & ~2 | 3;  // Represents clause (x1 v ~x2 v x3)
```
This keeps the logic for a single clause isolated and short.

**Step B: The Intermediate Batch Wires (`tcount_i`)**
Manthan iterates through the `t_` wires and ANDs them together. However, it maintains a counter `itr`. Every 100 clauses, it "flushes" the buffer into an intermediate wire called `tcount`.

**Code Logic (`src/convertVerilog.py`)**:
```python
while itr < count_tempvariable:
    temp_assign += "t_%s & " %(itr)
    
    # THE CUT-OFF: Every 100 clauses
    if itr % 100 == 0: 
        declare_wire += "wire tcount_%s;\n" %(itr)
        # Flush the buffer into a tcount wire
        assign_wire += "assign tcount_%s = %s;\n" %(itr,temp_assign.strip("& "))
        # Add this batch wire to the final output string
        outstr += "tcount_%s & " %(itr)
        temp_assign = '' # Reset buffer
    itr += 1
```

**Step C: The Final Assembly**
The final output `out` is not an AND of clauses, but an AND of the `tcount` batches.

```verilog
assign out = tcount_100 & tcount_200 & tcount_300 ...;
```

**Result**: Instead of one line with 100,000 tokens, you have 1,000 lines with 100 tokens each, and one final line with 1,000 tokens. This is trivially parsable.

### 2. Skolem Equality Batching (The "10-Batch" Rule)
**Source**: `src/createSkolem.py` -> `createSkolem`

Inside the `SKOLEMFORMULA` module, Manthan must verify that every candidate function prediction matches the expected input $Y'$.

**Logic**: `(Predicted_Y1 XNOR Input_Y1) AND (Predicted_Y2 XNOR Input_Y2) ...`
Since there can be thousands of outputs, Manthan applies an even stricter batching rule here: **Groups of 10**.

**The `wt_` Wires**
Manthan generates XNOR checks `(~(w_var ^ o_var))` and accumulates them.

**Code Logic (`src/createSkolem.py`)**:
```python
outstr += "(~(w%s ^ o%s)) & " % (var,var) # The XNOR Check

# THE CUT-OFF: Every 10 variables
if itr % 10 == 0:
    wirestr += "wire wt%s;\n" % (itr)
    # Flush buffer into intermediate wire
    assignstr += "assign wt%s = %s;\n" % (itr, outstr.strip("& "))
    wtlist.append(itr) # Keep track of the batch wires
    outstr = ''
```

The final output is an AND of these `wt` wires:
```python
for i in wtlist:
    assignstr += "wt%s & " % (i)
```

**Result**: The verification of the Skolem functions is broken down into tiny chunks, ensuring that the equality check logic never exceeds reasonable line lengths.

### 3. Structural Instantiation (The MAIN Module)
**Source**: `src/createSkolem.py` -> `createErrorFormula`

Manthan avoids creating a single monolithic file with mixed namespaces. It creates a top-level `MAIN` module that acts strictly as a wiring harness.

**Positional Port Mapping**
Manthan uses positional arguments for module instantiation, which is standard in Verilog 1995 but risky if variable orders change. Manthan mitigates this by generating the module definitions and the instantiations from the same ordered lists (`Xvar` and `Yvar`).

**The Wiring**:
```verilog
module MAIN ( ... inputs ... );
    // ... input decls ...
    
    // Explicit Wires for Sub-module outputs
    wire out1; 
    wire out2;
    wire out3;

    // Component 1: Is Specification Satisfiable?
    FORMULA F1 (2, 1, 3, 4, 5, out1 ); 

    // Component 2: Do Candidates Match Inputs?
    SKOLEMFORMULA F2 (2, ip1, ip3, ip4, ip5, out2 );

    // Component 3: Is Specification Valid for Candidates?
    FORMULA F2 (2, ip1, ip3, ip4, ip5, out3 );

    // Final Logic: (Sat_Spec) AND (Candidates_Match) AND (Result_Invalid)
    assign out = ( out1 & out2 & ~(out3) );
endmodule
```

**Why this is "Safe" Verilog**
- **No generate loops**: Loops are unrolled by Python into explicit wire declarations.
- **No always blocks**: All logic is `assign`. This avoids potential latches or sensitivity list issues in older parsers.
- **Strict Intermediate buffering**: The batching of clauses (100) and equality checks (10) ensures that the Abstract Syntax Tree (AST) depth for any single statement remains shallow, preventing stack overflows in recursive descent parsers used by tools like ABC.



## Technical Specification: The Manthan Refinement Loop

The Refinement loop is triggered when the verification step returns a counterexample $\sigma$. The goal is to modify the candidate functions $\Psi$ so they produce a valid output for $\sigma$ without breaking previously valid behaviors.

The process consists of two distinct phases:
1. **Fault Localization (MaxSAT)**: Identifying which candidates are responsible for the error.
2. **Repair Synthesis (UnsatCore)**: Modifying the logic of those identified candidates.

### Phase 1: Fault Localization (The MaxSAT Query)

**Code References**: `callMaxsat`, `callRC2`, `maxsatContent`, `addXvaluation` in `repair.py`.

Before fixing anything, Manthan must decide which variables to blame. The counterexample $\sigma$ tells us that $\Psi(X)$ is invalid, but it doesn't say why. Changing a "root" variable might fix the output, or changing a "leaf" variable might fix it. Manthan uses MaxSAT to make this decision optimal.

#### Step 1.1: Constructing the WCNF (Weighted CNF)

The function `maxsatContent` converts the original CNF specification into a format suitable for a MaxSAT solver.

**Hard Constraints ($W_{top}$)**:
- The original specification clauses $F(X, Y)$.
- The input constraints: $X \leftrightarrow \sigma[X]$. (Implemented in `addXvaluation`).

**Semantics**: "We must find a valid solution $Y$ for this specific input $X$."

**Soft Constraints ($W_{soft}$)**:
- For every output variable $y_i$, add a clause: $(y_i \leftrightarrow \sigma[y'_i])$.
- Where $\sigma[y'_i]$ is the value predicted by the current (buggy) candidate function.

**Semantics**: "Ideally, we want the new solution $Y$ to match our current function predictions as much as possible."

#### Step 1.2: Solving (Manthan vs. Manthan2)

The solver tries to satisfy all hard constraints while maximizing the weight of satisfied soft constraints. The variables associated with unsatisfied soft constraints are the ones that must change.

**Manthan (Standard MaxSAT)**:
- **Function**: `callMaxsat`.
- **Weights**: All soft constraints have weight = 1.
- **Logic**: Finds the minimum number of variables that need to change. If changing $y_{root}$ or $y_{leaf}$ both work, it picks arbitrarily.
- **Output**: Returns a list `indlist` of variables that flipped.

**Manthan2 (Lexicographic MaxSAT)**:
- **Function**: `callRC2`.
- **Weights**: Calculated based on Topological Order (`YvarOrder`).

```python
# repair.py
yindex = np.where(yvar == YvarOrder)[0][0]
weight = len(Yvar) - yindex
```

- Root variables get High weights.
- Leaf variables get Low weights.
- **Logic**: The solver is mathematically forced to preserve Root variables if possible. It will prefer flipping a Leaf variable (low cost) over a Root variable (high cost).
- **Output**: `indlist` containing the optimal set of repair candidates.

### Phase 2: Repair Synthesis (The Refinement Loop)

**Code Reference**: `repair` function in `repair.py`.

Manthan now iterates through the `indlist` (the "blame list") to synthesize patches.

#### Step 2.1: Context Definition

For the current variable being repaired (`repairvar` or $y_k$), Manthan strictly defines which variables it is allowed to see to prevent cycles.

1. It looks up $y_k$ in `YvarOrder`.
2. It defines `allowed_Y` as only those variables appearing after $y_k$ in the topological order (upstream dependencies).

#### Step 2.2: The Verification Query ($G_k$)

Manthan constructs a specific SAT query to generate the logic for the patch.

**Function**: `findUnsatCore`.

**Formula $G_k$**:

$$ G_k = F(X, Y) \land (X \leftrightarrow \sigma[X]) \land (\forall y \in allowed\_Y, y \leftrightarrow \sigma[y]) \land (y_k \leftrightarrow \sigma[y'_k]) $$

**Semantics**: "Is it possible for the specification to hold if $y_k$ keeps its current (allegedly wrong) value, assuming all inputs and upstream variables are fixed to the context?"

**Outcome**:
- **SAT**: It is possible! The MaxSAT blame was likely imprecise or the error is actually in a downstream variable we haven't checked yet. Manthan adds the current variable to `satvar` (skipped) and potentially expands the `ind` list.
- **UNSAT**: It is impossible. The value $\sigma[y'_k]$ is definitely wrong for this context. We need a patch.

#### Step 2.3: UnsatCore Extraction

Since $G_k$ is UNSAT, Manthan asks the SAT solver (PicoSAT) for the UnsatCore.

**Function**: `findUNSATCorePicosat`.

**Result**: A subset of literals from the constraints in Step 2.2 that caused the contradiction.

**Example Core**: $\{ x_1, \neg x_3, y_{upstream} \}$.

#### Step 2.4: Patch Construction ($\beta$)

Manthan converts the UnsatCore into a boolean formula $\beta$.

- **Filtering**: The code explicitly iterates through the core and discards any variable not in `allowed_Y` or `X`. This is a safety check to enforce acyclicity.
- **Construction**:
    - If core has $x_1$ (fixed to 1), $\beta$ adds `i1`.
    - If core has $y_j$ (fixed to 0), $\beta$ adds `~o_j`.
    - $\beta = i_1 \land \dots \land \neg o_j$.

#### Step 2.5: Verilog Modification

**Code Reference**: `updateSkolem` in `repair.py`.

Finally, Manthan modifies the Verilog source file to apply the patch.

- **New Wire**: It writes the $\beta$ formula to a new wire `beta_y_k`.
- **Logic Update**:
    - If the original function output 0 but needed 1:
        `assign w_new = ( (w_old) | (beta_y_k) );`
    - If the original function output 1 but needed 0:
        `assign w_new = ( (w_old) & ~(beta_y_k) );`

### Summary Flow

1. **Verification Fails** $\to$ Counterexample $\sigma$.
2. **MaxSAT Query**: "Find the best set of variables to flip to make $\sigma$ valid." $\to$ Returns `indlist`.
3. **Loop `indlist`**:
    - **Check**: "Is this variable truly broken given its upstream context?" ($G_k$ Query).
    - **Extract**: "What specific conditions make it broken?" (UnsatCore).
    - **Patch**: "Update the function to handle this exception." (Verilog rewrite).
4. **Repeat**: Until verification passes.



## Repair Loop Notes

### 1. Prerequisites & Data Structures
To implement this, you need the following state available before entering the loop:

*   **The Specification**: $F(X, Y)$ (CNF).
*   **The Candidates**: $\Psi = \{ \psi_1, \dots, \psi_m \}$ (Current boolean definitions for outputs $Y$).
*   **The Dependency Order**: `YvarOrder` (A topological sort of $Y$ where $y_i$ appears before $y_j$ if $y_i$ is independent of $y_j$. Note: Manthan often treats index 0 as "most dependent" in some contexts, but strictly `allowed_Y` logic defines the safe direction).
*   **The Counterexample**: $\sigma$ (An assignment to $X$ and $Y'$ where $F(X, \Psi(X))$ is False, but $F(X, Y)$ is True).

### 2. Phase I: Fault Localization (Who is wrong?)
**Goal**: Identifying the minimal set of functions that must change.

#### The MaxSAT Formulation
You must construct a Partial MaxSAT query.

*   **Hard Constraints (Infinite Weight)**:
    *   $F(X, Y)$ must be TRUE.
    *   $X$ must match the counterexample $\sigma[X]$.
    *   *Implementation*: Convert these to CNF unit clauses (e.g., if $\sigma[x_1]=1$, add clause $(x_1)$).
*   **Soft Constraints (Finite Weight)**:
    *   $y_i \leftrightarrow \sigma[y'_i]$ (The new solution should match the current function's output).
    *   *Implementation*: Add unit clauses with weights.

#### Algorithm Selection (Manthan 1 vs 2)
*   **Standard MaxSAT (Manthan 1)**: Assign weight 1 to all soft constraints. This minimizes the count of changed functions.
*   **Lexicographic MaxSAT (Manthan 2 - Recommended)**: Assign weights based on `YvarOrder`.
    *   **Weighting Strategy**: $Weight(y_i) \gg Weight(y_j)$ if $y_i$ is upstream (an input to) $y_j$.
    *   **Why**: This forces the solver to blame the "root cause" rather than a symptom. If $y_{root}$ is wrong, fixing it is "expensive" (high weight), but the solver is forced to if preserving it makes the hard constraints unsatisfiable.

**Output**: A list `ind` (indices) of variables where the soft constraint was violated.

### 3. Phase II: The Repair Loop (Iterative Patching)
**Goal**: Iterate through `ind` and synthesize a boolean patch for each.

**State Variables**:
*   `repaired`: List of variables fixed in this loop.
*   `satvar`: List of variables we tried to fix but couldn't (the hypothesis failed).

**Loop Logic**:
Iterate through `ind`. For each `repairvar` ($y_k$):

#### Step A: Dependency Filtering (`allowed_Y`)
You must define the "Context" for $y_k$. To prevent cycles, $y_k$ can only look at variables that are topologically "upstream".

**Implementation**:
```python
index = YvarOrder.indexOf(y_k)
allowed_Y = YvarOrder[index:] # Slicing the sorted list
```
*Note: This assumes your order is [Dependent ... Independent]. Adjust slice direction based on your sort.*

#### Step B: The Hypothesis Query ($G_k$)
Construct a SAT formula to check if $y_k$ is the culprit.

**Formula**: 
$$ G_k = F(X, Y) \land (X \leftrightarrow \sigma[X]) \land (y_k \leftrightarrow \sigma[y'_k]) $$

**Upstream Constraints**: 
For every $y_j \in allowed\_Y$:
*   Add constraint $y_j \leftrightarrow \sigma[y_j]$. (Fix upstream vars to the valid solution found by the SAT oracle).
*   **Crucial**: Do NOT constrain downstream variables. Leave them free.

**Query**: Is $G_k$ Satisfiable?

#### Step C: Handling the Result

**Case 1: SAT (False Alarm)**
*   **Meaning**: The specification can be satisfied even if $y_k$ takes the "wrong" value. The error is likely downstream.
*   **Action**:
    *   Add $y_k$ to `satvar`.
    *   **Dynamic Expansion**: The SAT solver returned a valid model $Y_{new}$. Compare $Y_{new}$ to your candidates $\Psi$. Any mismatch not currently in `ind` should be added to `ind`. This finds the downstream symptom you missed.

**Case 2: UNSAT (Confirmed Fault)**
*   **Meaning**: It is impossible for $y_k$ to take value $\sigma[y'_k]$ given the inputs and upstream context.
*   **Action**: Call UnsatCore extraction on the solver.

### 4. Phase III: Patch Synthesis (The UnsatCore)
**Goal**: Turn the "reason for UNSAT" into a boolean function.

The UnsatCore is a list of literals from your constraints (Inputs and Upstream Fixed Vars) that caused the conflict.
Let Core $C = \{ l_1, l_2, \dots, l_n \}$.

*   **Filtering**: Discard any literal referring to a variable not in $X$ or `allowed_Y`. (Safety check).
*   **The Patch Formula ($\beta$)**: $\beta = \bigwedge_{l \in C} l$
    *   *Example*: If Core is $\{x_1, \neg y_2\}$, then $\beta = (x_1 \land \neg y_2)$.

### 5. Phase IV: Function Update (Verilog Composition)
**Goal**: Update the logic of $\psi_k$ to handle this exception.

You are modifying the boolean function $\psi_k$.
Let **Target** be the value $y_k$ should have had (the valid value from $\sigma$, i.e., $\neg \sigma[y'_k]$).

**The Update Logic**:
*   If **Target is 1** (Current is 0):
    *   You need to force the function to 1 when $\beta$ is true.
    *   $\psi_{new} = \psi_{old} \lor \beta$
*   If **Target is 0** (Current is 1):
    *   You need to force the function to 0 when $\beta$ is true.
    *   $\psi_{new} = \psi_{old} \land \neg \beta$