RegionAI – Multi-Space Design Document

Generated 2025-07-15 – distilled from discussion thread

────────────────────────────────────────
1. Design Motivation
────────────────────────────────────────
The original RegionAI vision assumed a single high-dimensional region space to host every concept, transformation, and user preference.

Real-world workloads (fictional world-building, per-user customization, scientific law discovery) expose three hard limits of “one space to rule them all”:

- Inconsistent Ontologies – fantasy physics vs. real physics cannot coexist in one geometry without contradiction or dimensionality explosion.  
- Preference Fragmentation – Alice’s “tasty” region and Bob’s incompatible “tasty” region force an ever-growing, fuzzy global volume.  
- Hypothesis Space Complexity – discovering the inverse-square law from raw planetary data requires reasoning in function space, not raw data space.

We therefore introduce a tiered, multi-space architecture that keeps RegionAI’s bootstrapping philosophy while removing the single-space limitation.

────────────────────────────────────────
2. Architectural Tiers
────────────────────────────────────────
Tier 1 – Bootstrap Kernel (immutable)  
- Region algebra: containment, overlap, join/meet, fuzzy boundaries, hierarchical sub-regions.  
- Logical connectives encoded as region operations (∧, ∨, ¬, ⇒).  
- Discovery engine primitives: sequential, conditional, iterative composition strategies.  
- Abstract interpretation lattice (sign, range, nullability, widening operators).  
- Minimal language glue: tokeniser, pronoun resolution, beam-search disambiguation.  
- Versioned and cryptographically signed; never mutated at runtime.

Tier 2 – Domain Modules (hot-swappable libraries)  
- Mathematics: arithmetic, algebra, induction schemas, numeric ranges.  
- Physics-Priors: inverse-square hypothesis class, conservation laws, units.  
- Linguistics: grammar rules, morphology, dependency patterns.  
- Common-Sense: object permanence, gravity, time ordering, social defaults.  
- Each module is a region bundle that can be loaded, unloaded, or locally overridden without touching the kernel.

Tier 3 – Epistemic Workspaces (per-use-case spaces)  
- Lightweight instantiation: `Workspace(name, bootstrap_version)`  
- Module loading: `ws.load_module("physics", overrides={G: 42})`  
- User forks: `alice = ws.fork("alice_42")`  
- Cross-space morphisms:  
  
```python
  from regionai.morphism import Morphism, linear_map
  Morphism.register(
      from_space = physics_ws,
      to_space   = fantasy_ws,
      transform  = λvec: apply_magic_constants(vec)
  )
  ```

────────────────────────────────────────
3. Lifecycle from Cold-Start to AGI
────────────────────────────────────────
Step 0 – Kernel Only  
- Source: < 2 kLoC, formally audited.  
- Inputs: raw keyboard logs, sensor streams, text dumps.

Step 1 – Automatic Tier-2 Bootstrapping  
- Discovery engine ingests raw data → induces arithmetic module, basic physics, POS grammar.  
- Produces signed `.mod` bundles stored in Tier-2 repository.

Step 2 – User & World Instantiation  
- Alice says “I hate cilantro” → system forks workspace, records negative preference region.  
- Fantasy writer declares “dragons ignore gravity” → forks workspace, remaps physics morphism.  
- No human authored rules; everything is learned as transformations on regions.

Step 3 – Self-Analysis Loop  
- System analyses its own source → creates workspace `regionai-self`.  
- Runs static analysis → discovers latent bug → generates patch → proves sound → commits.  
- Kernel guarantees that proofs remain valid against immutable Tier-1 axioms.

Step 4 – AGI Threshold  
- Metric: average time between fully autonomous capability jumps (new module, new morphism, new self-patch) < human reaction time.  
- Result: continuous, unattended expansion of capabilities across scientific, linguistic, creative, and personal domains.

────────────────────────────────────────
4. Detailed API Surface
────────────────────────────────────────

```python
# Tier-1 Kernel (immutable)
from regionai.kernel import Kernel
kernel = Kernel(version="1.4.0")          # frozen

# Tier-2 Module Management
from regionai.modules import ModuleHub
hub = ModuleHub(kernel=kernel)
math = hub.load("mathematics")            # returns region bundle
physics = hub.load("physics", overrides={"G": 6.67430e-11})

# Tier-3 Workspace API
from regionai.workspace import Workspace, Morphism
ws = Workspace("fantasy_world", kernel=kernel)
ws.import_bundle(math)
ws.import_bundle(physics, override={"G": 42})

# Forking & Morphisms
alice = ws.fork("alice_prefs")
alice.add_region("tasty", centroid=cilantro_vec, radius=0.1)
Morphism.register(
    from_space=ws.physics,
    to_space=ws.magic,
    transform=λv: magic_substitution_matrix @ v
)

# Discovery Engine still Tier-1
from regionai.kernel.discovery import discover
law = discover(
    problems=[(r, F) for planet in ephemerides],
    strategy="iterative"
)  # returns inverse-square transformation region
```

────────────────────────────────────────
5. Storage & Versioning
────────────────────────────────────────
- Kernel: read-only, Git-tag signed.  
- Modules: content-addressed bundles (sha256.mod).  
- Workspaces: Merkle-tree snapshots enabling deterministic replay and audit.  
- Morphism registry: append-only log with cryptographic proofs of validity against Tier-1 axioms.

────────────────────────────────────────
6. Security & Consistency Guarantees
────────────────────────────────────────
- Soundness: Any transformation admitted by Tier-1 is logically sound relative to the kernel axioms.  
- Isolation: A corrupted fantasy workspace cannot poison physics or mathematics modules.  
- Upgrade Path: Kernel upgrades require external consensus (formal proof + multisig) because they modify the bootstrapping foundation.

────────────────────────────────────────
7. Migration Path from Current Single-Space Prototype
────────────────────────────────────────
1. Refactor existing `src/regionai/*` into `src/tier1/*` (kernel) and `src/tier2/*` (modules).  
2. Introduce `src/tier3/workspace.py` and `src/tier3/morphism.py`.  
3. Provide compatibility shim so legacy single-space code runs inside a default workspace named `"legacy"` with full module set loaded.  
4. Deprecation window: two minor releases, then remove shim.

────────────────────────────────────────
8. Checklist for Repo Integration
────────────────────────────────────────
- Create `docs/design/multi-space.md` (this file).  
- Move immutable kernel sources to `src/tier1/`.  
- Create `modules/` directory for Tier-2 bundles.  
- Implement `src/tier3/workspace.py` and `morphism.py`.  
- Add CLI: `regionai workspace create <name>` and `regionai module install <name>`.  
- Update CI to gate kernel changes behind formal proof job.  
- Update README to reference this document.

────────────────────────────────────────
End of Document