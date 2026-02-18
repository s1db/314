## Variable Dependencies in QBFs

A direct SAT-style backdoor doesn't work for QBFs because of **variable dependencies**. The order of quantifiers ($\forall, \exists$) matters immensely in QBF solving.

Let's look at a new formula:
$\mathcal{F}_2 = \forall y \exists z \exists x \; (x \lor z \lor y)$

Here, the problem is the 3-literal clause $(x \lor z \lor y)$. A naive SAT approach might be to make a backdoor $B=\{x\}$, since $x$ is in the clause we want to simplify.

But in the prefix of the QBF $\forall y \exists z \exists x...$, the value of $x$ can *depend* on the value chosen for $y$. A critical requirement for QBF backdoors is that they must be **closed under this dependency**. I.e if you put a variable $x$ into the backdoor, you *must also* include all the variables $x$ depends on.

In this case, $x$ depends on $y$. Therefore, a valid, dependency-closed backdoor wouldn't be $\{x\}$, it would have to be $B' = \{x, y\}$.

This forces the development of a "theory of variable dependency".

A naïve rule (e.g., "a variable depends on everything quantified to its left") is too restrictive and would make all backdoors enormous. A more sophisticated approach is needed to find the *true* dependencies. For example, if we can prove that $\forall y \exists z$ can be "swapped" to $\exists z \forall y$ without changing the formula's satisfiability, we've proven that $z$ *doesn't* depend on $y$, which gives us more succinct backdoor sets.

Proposition 2 of @samer_backdoor_2009 shows that finding minimum variable dependencies is PSPACE-hard.

## Tractable Dependency Schemes

While finding the minimum dependency schemes is PSPACE-hard, there exist some tractable algorithms for computing minimal dependency schemes. Before we describe the schemes, we define the following:

* $R_{\mathcal{F}}$ is a binary relation that identifies all pairs of variables $(x, y)$ where $x$ is quantified to the left of $y$ in the formula's prefix (i.e., the depth of $x$ is less than the depth of $y$). Therefore, $R_{\mathcal{F}}(x)$ is the set of all variables that are on the right of $x$ in the quantifier prefix.

### Trivial Scheme

The Trivial Dependency Scheme ($D^{trv}$) is a basic, safe, and tractable method for assigning dependencies in a Quantified Boolean Formula (QBF).

The scheme is defined as assigning to each QCNF formula $\mathcal{F}$ the binary relation $R_{\mathcal{F}}^{\circ}$, defined as follows:

> $R_{\mathcal{F}}^{\circ}$: Assigning to each variable $x$ all the variables $y$ to its right in the quantifier prefix, but only starting from the first variable (from left to right) that has a different quantification type.

> [!example]- An Example of the Trivial Dependency Scheme Computation
>
>Consider the formula: $\mathcal{F} = \forall a \forall b \exists c \exists d \forall e$.
>
>The prefix is ordered as follows: $a < b < c < d < e$. The quantifier blocks are:
>
>* **Block 1 ($\forall$):** $\{a, b\}$
>* **Block 2 ($\exists$):** $\{c, d\}$
>* **Block 3 ($\forall$):** $\{e\}$
>
>Now let's compute the dependencies ($D^{trv}$) for each variable:
>
>* $D^{trv}(a) = \{c,d,e\}$. Note: $b$ is not included, even though it is to the right of it because it appears in the same quantifier block as $a$.
>* $D^{trv}(b) = \{c,d,e\}$
>* $D^{trv}(c) = \{e\}$
>* $D^{trv}(d) = \{e\}$
>* $D^{trv}(e) = \emptyset$
>
>This gives us the partial ordering: $a~b < c~d < e$, where the ordering of $a$ and $b$, and $c$ and $d$ can be changed as they're in the same quantifier block.

### Standard Scheme

The Standard Dependency Scheme ($D^{std}$) is "more general" (i.e., more precise) than $D^{trv}$ because it analyzes the formula's clause structure, not just the quantifier prefix.

#### Core Ideas

The scheme is based on an approach of "connectedness", presented in @hutchison_resolve_2005 and later refined in @marques-silva_bounded_2007.

* **Biere's Idea:** The paper states that two variables ($x, y$) are "locally connected" if they appear in the same clause. They are "connected" if there is a path of such locally connected variables between them.
* **Bubeck and Kleine Büning's Refinement:** The paper incorporates their observation that universally quantified ($\forall$) variables should be ignored when building this connection path. The reasoning is that universal variables do not propagate changes of truth values.

$D^{std}$ formalizes this "connected-while-ignoring-universals" idea.

#### Formal Definitions

The scheme relies on three preliminary definitions that build upon each other:

* **Set $X$**: $X = R_{\mathcal{F}}(x) \setminus var_{\forall}(\mathcal{F})$

  In plain English, this means:
  * $R_{\mathcal{F}}(x)$: "all variables to the right of $x$ in the prefix"
  * $\setminus var_{\forall}(\mathcal{F})$: "minus all the universal variables"

  Therefore, the set $X$ is "the set of all existential ($\exists$) variables that are to the right of $x$."

* **Connected:** An X-path between two clauses $C$ and $C'$ is a sequence of clauses ($C_1, \dots, C_n$ where $C_1=C$ and $C_n=C'$). In this path, any two adjacent clauses ($C_i, C_{i+1}$) must share at least one variable that is in the set $X$. Two clauses are connected with respect to $X$ if such an X-path exists between them.

* **Dependency Pair:** An (x, y)-dependency pair with respect to a set $X$ is a pair of clauses $(C, C')$ that meets three conditions:
  * $x$ and $y$ must have different quantifier types ($q_{\mathcal{F}}(x) \neq q_{\mathcal{F}}(y)$).
  * $x$ must be in clause $C$ and $y$ must be in clause $C'$.
  * $C$ and $C'$ must be **"connected"** with respect to the **set $X$**.

Using these we can define the $D^{std}$ Rule as follows:

> A variable $y$ depends on $x$ (i.e., $(x, y) \in D_{\mathcal{F}}^{std}$) if and only if:
>
> 1. $y$ is to the right of $x$ in the prefix ($y \in R_{\mathcal{F}}(x)$).
> 2. The formula $\mathcal{F}$ contains an (x, y)-dependency pair.
> 3. The "connection set" $X$ used to check for the dependency pair is defined as: $X = R_{\mathcal{F}}(x) \setminus var_{\forall}(\mathcal{F})$.

> [!example]- An Example of the Standard Dependency Scheme Computation
>Let's analyze the following formula:
>$$
>\mathcal{F} = \forall u\exists v\forall w\exists x\forall y\exists z(u\vee\neg v\vee x)\wedge(u\vee\neg x)\wedge(v\vee z)\wedge(v\vee\neg z)\wedge(w\vee x\vee y)\wedge(y\vee\neg z)
>$$
>
>Let the clauses in $\mathcal{F}$ be labeled as $C_1,...,C_6$.
>
>Here,
>
>* $D_{\mathcal{F}}^{std}(u) = \{v, x, z\}$
>   * $X= \{v, x, z\}$
>   * Check `(u, v)`: `u` ($\forall$) and `v` ($\exists$) have different quantifiers and they are connected by clause $C_1$.
>     * $v \in D_{\mathcal{F}}^{std}(u)$.
>   * Check `(u, x)`: `u` ($\forall$) and `x` ($\exists$) have different quantifiers and they are connected by clause $C_1$ (and via clause $C_2$).
>     * $x \in D_{\mathcal{F}}^{std}(u)$.
>   * Check `(u, z)`: `u` ($\forall$) and `z` ($\exists$) have different quantifiers and they are connected by the path u (C1) → v → (C3) z. As $v \in X$, it's a valid connection.
>     * $z \in D_{\mathcal{F}}^{std}(u)$.
>* $D_{\mathcal{F}}^{std}(v) = \{w, y\}$
>   * $X= \{x,z\}$
>   * Check `(v, w)`: `v` ($\exists$) and `w` ($\forall$) have different quantifiers and they are connected by the path v (C1) → x → (C5) w. As $x \in X$, it's a valid connection.
>     * $w \in D_{\mathcal{F}}^{std}(v)$.
>   * Check `(v, y)`: `v` ($\exists$) and `y` ($\forall$) have different quantifiers and they are connected by the path v (C1) → x → (C5) y. As $x \in X$, it's a valid connection.
>     * $y \in D_{\mathcal{F}}^{std}(v)$.
>* $D_{\mathcal{F}}^{std}(w) = \{x\}$
>   * $X= \{x, z\}$
>   * Check `(w, x)`: `w` ($\forall$) and `x` ($\exists$) have different quantifiers and they are connected by clause $C_5$.
>     * $x \in D_{\mathcal{F}}^{std}(w)$
>   * Check `(w, z)`: `w` ($\forall$) and `z` ($\exists$) have different quantifiers and they are connected by the path w (C5) → y → z (C6). As $y \not \in X$, it's an invalid path.
>     * $z \not \in D_{\mathcal{F}}^{std}(w)$
>* $D_{\mathcal{F}}^{std}(x) = \{y\}$
>   * $X = \{z\}$
>   * Check `(x, y)`: `x` ($\exists$) and `y` ($\forall$) have different quantifiers and they are connected by clause $C_5$.
>     * $y \in D_{\mathcal{F}}^{std}(x)$
>* $D_{\mathcal{F}}^{std}(y) = \{z\}$
>   * $X = \{z\}$
>   * Check `(y, z)`: `y` ($\forall$) and `z` ($\exists$) have different quantifiers and they are connected by clause $C_6$.
>     * $z \in D_{\mathcal{F}}^{std}(y)$
>* $D_{\mathcal{F}}^{std}(z) = \emptyset$
>   * $X = \emptyset$

### Triangle Scheme

#### Core Idea

The Triangle Dependency Scheme $D^{\Delta}$ is a far stricter dependency than $D^{std}$. For a dependency to exist, it must find a specific "triangle" of connections involving both the positive and negative literals of a variable.

The key intuition is:

* If a universal variable $x$ ($\forall$) is connected to a clause containing the positive literal $y$ ($\exists$) AND also connected to a clause containing the negative literal $\neg y$, then $y$'s value is truly dependent on $x$.
* If $x$ is only connected to one of them (e.g., $y$ but not $\neg y$), then $y$ is considered *"pure"* (think [[unate|unate]]/monotonic) **relative to $x$**, and $D^{\Delta}$ concludes there is no dependency.

#### Formal Definition

The scheme relies on the following definition:

* **Set $X$**: $X = R_{\mathcal{F}}(x) \setminus var_{\forall}(\mathcal{F}) \cup \{x\}$.

* **Dependency Triple:** This is a triple of clauses $(C_1, C_2, C_3)$ that "proves" a dependency between $x$ and $y$ (which must have different quantifier types). The definition has two cases:
  * **Case 1:** $x$ is $\forall$, $y$ is $\exists$ then $C_1$ must contain $x$.
    * $C_2$ must contain the positive literal $y$.
    * $C_3$ must contain the negative literal $\neg y$.
    * The "Triangle": $C_1$ must be connected to $C_2$, AND $C_1$ must also be connected to $C_3$ with respect to $X \cup \{x\}$.
  * **Case 2:** $x$ is $\exists$, $y$ is $\forall$ then $C_1$ must contain $y$.
    * $C_2$ must contain the positive literal $x$.
    * $C_3$ must contain the negative literal $\neg x$.
    * The "Triangle": $C_1$ must be connected to $C_2$, AND $C_1$ must also be connected to $C_3$ with respect to $X \cup \{y\}$.

> A variable $y$ depends on $x$ (i.e., $(x, y) \in D_{\mathcal{F}}^{\Delta}$) if and only if:
>
> 1. $y$ is to the right of $x$ in the prefix ($y \in R_{\mathcal{F}}(x)$).
> 2. The formula $\mathcal{F}$ contains an (x, y)-dependency triple.
> 3. The "connection set" $X$ used to check for the dependency pair is defined as: $X = R_{\mathcal{F}}(x) \setminus (var_{\forall}(\mathcal{F}) \cup \{y\})$.

> [!example]- An Example of the Triangle Dependency Scheme Computation
> Let's analyze the same formula we used for $D^{std}$:
>$$
>\mathcal{F} = \forall u\exists v\forall w\exists x\forall y\exists z(u\vee\neg v\vee x)\wedge(u\vee\neg x)\wedge(v\vee z)\wedge(v\vee\neg z)\wedge(w\vee x\vee y)\wedge(y\vee\neg z)
>$$
>
> Let the clauses in $\mathcal{F}$ be labeled as $C_1,...,C_6$.
> Here,
>
>* $D_{\mathcal{F}}^{\Delta}(u) = \{x, z\}$
>   * As u is $\forall$, we need to check against all $\exists$ variable that are in $R_{\mathcal{F}}(u)$ using case 1.
>   * $X= \{v, x, z\} \cup \{u\}$
>   * Check `(u, v)`: `u` ($\forall$) and `v` ($\exists$).
>     * We require the triple: $(C_u, C_v, C_{\neg v})$, let's use $(C_1, C_3, C_1)$.
>     * $C_1 = (u\vee\neg v\vee x)$ and $C_3 = (v\vee z)$ aren't connected using the variables in $X$.
>     * As $C_1$ and $C_3$ are not connected:
>       * $v \not \in D_{\mathcal{F}}^{\Delta}(u)$
>   * Check `(u, x)`: `u` ($\forall$) and `x` ($\exists$).
>     * We require the triple: $(C_u, C_x, C_{\neg x})$, let's use $(C_1, C_1, C_2)$.
>     * $C_1 = (u ∨ ¬v ∨ x)$ and $C_1 = (u ∨ ¬v ∨ x)$ are connected trivially.
>     * $C_1 = (u ∨ ¬v ∨ x)$ and $C_3 = (v\vee z)$ are connected via $v \in X$.
>     * As $C_1$ and $C_1$ and $C_1$ and $C_3$ are connected:
>       * $x \in D_{\mathcal{F}}^{\Delta}(u)$
>   * Check `(u, z)`: `u` ($\forall$) and `z` ($\exists$).
>     * We require the triple: $(C_u, C_z, C_{\neg z})$, let's use $(C_1, C_3, C_4)$.
>     * $C_1 = (u\vee\neg v\vee x)$ and $C_3 = (v\vee z)$ are connected via $v \in X$.
>     * $C_1 = (u\vee\neg v\vee x)$ and $C_4 = (v\vee \neg z)$ are connected via $v \in X$.
>     * As $C_1$ and $C_3$ and $C_1$ and $C_4$ are connected:
>       * $z \in D_{\mathcal{F}}^{\Delta}(u)$
>* $D_{\mathcal{F}}^{\Delta}(v) = \{y\}$
>   * As v is $\exists$, we need to check against all $\forall$ variables that are in $R_{\mathcal{F}}(v)$ using case 2.
>   * Check `(v, w)`: `v` ($\exists$) and `w` ($\forall$).
>     * $X = \{x, z\} \cup \{w\}$
>     * We require the triple: $(C_w, C_v, C_{\neg v})$, let's use $(C_5, C_3, C_1)$.
>     * $C_5 = (w\vee x\vee y)$ and $C_3 = (v\vee z)$ are not connected via $X$.
>     * As $C_5$ and $C_3$ are not connected:
>       * $w \not \in D_{\mathcal{F}}^{\Delta}(v)$
>   * Check `(v, y)`: `v` ($\exists$) and `y` ($\forall$).
>     * $X = \{x, z\} \cup \{y\}$
>     * We require the triple: $(C_y, C_v, C_{\neg v})$, let's use $(C_6, C_3, C_1)$.
>     * $C_6 = (y\vee \neg z)$ and $C_3 = (v\vee z)$ are connected via $z \in X$.
>     * $C_6 = (y\vee \neg z)$ and $C_1 = (u\vee\neg v\vee x)$ are connected via the path $C_6 ↔ y ↔ C_5 ↔ x ↔ C_1$.
>     * As $C_6$ and $C_3$ and $C_6$ and $C_1$ are connected:
>       * $y \in D_{\mathcal{F}}^{\Delta}(v)$
>* $D_{\mathcal{F}}^{\Delta}(w) = \emptyset$
>   * As w is $\forall$, we need to check against all $\exists$ variables that are in $R_{\mathcal{F}}(w)$ using case 1.
>   * $X = \{x, z\} \cup \{w\}$
>   * Check `(w, x)`: `w` ($\forall$) and `x` ($\exists$).
>     * We require the triple: $(C_w, C_x, C_{\neg x})$, let's use $(C_5, C_5, C_2)$.
>     * $C_5 = (w\vee x\vee y)$ and $C_5 = (w\vee x\vee y)$ are connected trivially.
>     * $C_5 = (w\vee x\vee y)$ and $C_2 = (u \vee \neg x)$ are not connected via $X$.
>     * As $C_5$ and $C_5$ is connected and $C_5$ and $C_2$ are not connected:
>       * $x \not \in D_{\mathcal{F}}^{\Delta}(w)$
>   * Check `(w, z)`: `w` ($\forall$) and `z` ($\exists$).
>     * We require the triple: $(C_w, C_z, C_{\neg z})$, let's use $(C_5, C_3, C_4)$.
>     * $C_5 = (w\vee x\vee y)$ and $C_3 = (v\vee z)$ are not connected via $X$.
>     * As $C_5$ and $C_3$ are not connected:
>       * $w \not \in D_{\mathcal{F}}^{\Delta}(w)$
>* $D_{\mathcal{F}}^{\Delta}(x) = \emptyset$
>   * As x is $\exists$, we need to check against all $\forall$ variables that are in $R_{\mathcal{F}}(x)$ using case 2.
>   * Check `(x, y)`: `x` ($\exists$) and `y` ($\forall$).
>     * $X = \{z\} \cup \{y\}$
>     * We require the triple $(C_y, C_x, C_{\neg x})$, let's use $(C_5, C_5, C_2)$.
>     * $C_5 = (w\vee x\vee y)$ and $C_5 = (w\vee x\vee y)$ are connected trivially.
>     * $C_5 = (w\vee x\vee y)$ and $C_2 = (u \vee \neg x)$ are not connected via $X$.
>     * As $C_5$ and $C_5$ is connected and $C_5$ and $C_2$ are not connected:
>       * $y \not \in D_{\mathcal{F}}^{\Delta}(x)$
>* $D_{\mathcal{F}}^{\Delta}(y) = \emptyset$
>   * As y is $\forall$, we need to check against all $\exists$ variables that are in $R_{\mathcal{F}}(y)$ using case 1.
>   * $X = \{\} \cup \{y\}$
>   * Check `(y, z)`: `y` ($\forall$) and `z` ($\exists$).
>     * We require the triple: $(C_y, C_z, C_{\neg z})$, let's use $(C_6, C_3, C_4)$.
>     * $C_6 = (y\vee \neg z)$ and $C_3 = (v\vee z)$ are not connected via $X$.
>     * As $C_6$ and $C_3$ are not connected:
>       * $z \not \in D_{\mathcal{F}}^{\Delta}(y)$
>
>* $D_{\mathcal{F}}^{\Delta}(z) = \emptyset$
>   * As z is $\exists$, we need to check against all $\forall$ variables that are in $R_{\mathcal{F}}(z)$ using case 2.
>   * As $R_{\mathcal{F}}(z)$ is the empty set, there is nothing to check.

### Trivial vs Standard vs Triangle Dependency Schemes

**Formula:** $\mathcal{F} = \forall u\exists v\forall w\exists x\forall y\exists z(u\vee\neg v\vee x)\wedge(u\vee\neg x)\wedge(v\vee z)\wedge(v\vee\neg z)\wedge(w\vee x\vee y)\wedge(y\vee\neg z)$

| Variable | $D^{trv}$ (Trivial) | $D^{std}$ (Standard) | $D^{\Delta}$ (Triangle) |
| :--- | :--- | :--- | :--- |
| **$D(u)$** | $\{v, w, x, y, z\}$ | $\{v, x, z\}$ | $\{x, z\}$ |
| **$D(v)$** | $\{w, x, y, z\}$ | $\{w, y\}$ | $\{y\}$ |
| **$D(w)$** | $\{x, y, z\}$ | $\{x\}$ | $\emptyset$ |
| **$D(x)$** | $\{y, z\}$ | $\{y\}$ | $\emptyset$ |
| **$D(y)$** | $\{z\}$ | $\{z\}$ | $\emptyset$ |
| **$D(z)$** | $\emptyset$ | $\emptyset$ | $\emptyset$ |

This table clearly shows the hierarchy of precision:

* The **Trivial** scheme is the most "pessimistic" and finds the most dependencies.
* The **Standard** scheme is more precise, finding a subset of the Trivial dependencies by analyzing the clause structure.
* The **Triangle** scheme is the most precise, finding the smallest set of dependencies.
* @samer_backdoor_2009 contains proofs that show $D_{\mathcal{F}}^{\Delta} \subseteq D_{\mathcal{F}}^{std} \subseteq D_{\mathcal{F}}^{trv}$.
