# Capability Test: Running OrdinaryDiffEq.jl From a Claude Code Web Session

> **Purpose:** Record what a Claude Code on the web session started against
> `TerceiraEvents/EventosTerceira.pt` can and cannot do with a large Julia
> package (OrdinaryDiffEq.jl) — building it, solving with it, testing it, and
> opening pull requests against it.
> **Date measured:** 2026-08-21
> **Container:** Ubuntu 24.04, 4 cores, 15 GB RAM, Julia 1.12.7, ~28 GB writable.

---

## Verdict

| Capability | Result |
| --- | --- |
| Clone OrdinaryDiffEq.jl | Yes — anonymous git read through the session proxy |
| Install its ~180 dependencies | Yes — a Julia package server is reachable |
| `using OrdinaryDiffEq` and solve | Yes — non-stiff and stiff, correct to tolerance |
| Run the test suite | Yes — see timings below |
| Run the formatter / spell checker | Yes — `runic` 1.9.0, `typos-cli` 1.49.0 |
| Commit locally and produce patches | Yes |
| **Push to SciML/OrdinaryDiffEq.jl** | **No** — proxy refuses to inject a credential |
| **Open a PR against SciML** | **No** — GitHub API is 403 for out-of-scope repos |

The compute side is fully capable. The blocker is purely the session's
repository authorization scope, and it has a known workaround (below).

## The access boundary

A session's GitHub access is fixed to the repositories it was started with.
Three independent probes agree:

1. Attaching the repo mid-session is refused outright:

   ```
   add_repo: cross-tier adds are not supported in v1: requested
   "sciml/ordinarydiffeq.jl" but session already has repos from owner(s)
   [terceiraevents]. Start a new session with the requested repo as the
   initial source, or add a repo from the same owner as the existing sources
   ```

2. The GitHub REST API refuses out-of-scope repos, while in-scope ones work:

   ```
   $ gh api repos/SciML/OrdinaryDiffEq.jl --jq .full_name
   gh: GitHub access to this repository is not enabled for this session. (HTTP 403)

   $ gh api repos/TerceiraEvents/EventosTerceira.pt --jq '.full_name,.default_branch'
   TerceiraEvents/EventosTerceira.pt
   main
   ```

3. Git writes are refused at the proxy, even though reads succeed:

   ```
   $ git push --dry-run origin HEAD:refs/heads/claude-write-probe
   remote: access denied by the git proxy: SciML/OrdinaryDiffEq.jl is not in this
   session's authorized repository set, so the proxy will not inject a credential
   for it. To fix, add the repository to the session's sources.
   fatal: unable to access '.../OrdinaryDiffEq.jl/': The requested URL returned error: 403
   ```

Reading is unrestricted — `git clone` of any public repo works, because that
path needs no credential.

**Workaround:** start the session with `SciML/OrdinaryDiffEq.jl` as its initial
source (the environment's repository source, or the initial `add_repo`). Then
push and PR work normally and this document's compute measurements apply
unchanged. A session already bound to another owner cannot be retrofitted.

## Build and solve evidence

Clone, then instantiate the main project:

```
$ git clone https://github.com/SciML/OrdinaryDiffEq.jl      # 85 MB, HEAD f2ebdb9a3
$ julia --project=. -e 'using Pkg; Pkg.instantiate()'
143 dependencies successfully precompiled in 509 seconds. 40 already precompiled.
real    8m42.450s
```

Then a non-stiff and a stiff solve, in a fresh session (`real 0m11.091s`
including the first `using OrdinaryDiffEq`):

```
retcode  = Success            # Tsit5, u' = 1.01u, u0 = 0.5, t ∈ [0,1], rtol = atol = 1e-8
u_end    = 1.3728005076225747
exact    = 1.3728005075084582
abserr   = 1.1411649403214597e-10
nsteps   = 17

rober retcode = Success       # Rodas5P, ROBER, t ∈ [0,1e5], rtol = atol = 1e-8
rober u_end   = [0.01786592083867249, 7.27475134266605e-8, 0.9821340064138143]
rober sum     = 1.0000000000000002
```

Both integrators return `Success`, the non-stiff error sits at the requested
tolerance, and ROBER conserves mass to one ulp.

## Package installation is fast here

Installing a small package into a temporary environment took **10.4 s** end to
end, and the registry updates as a compressed `~/.julia/registries/General.toml`
— both signs that a package server is reachable rather than Pkg falling back to
cloning the registry and every package over git. `JULIA_PKG_SERVER` is unset,
`JULIA_PKG_USE_CLI_GIT=true`, and `JULIA_SSL_CA_ROOTS_PATH` points at the
session's CA bundle. Earlier notes claiming this container has no package server
and needs ~12 minutes to fetch dependencies do not describe this image.

## Development tooling

`runic --check` and `typos` both run and report clean on the checkout, so the
pre-push checks that catch most first-push CI failures are available locally:

```
$ runic --version && runic --check lib/OrdinaryDiffEqCore/src   # exit 0
runic version 1.9.0, julia version 1.12.7
$ typos --version && typos src lib/OrdinaryDiffEqCore           # exit 0
typos-cli 1.49.0
```

