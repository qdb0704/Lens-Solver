# Publish To GitHub

This guide assumes you want to publish:

- local folder: `c:\SolverModule\public_kernel_solver_repo`
- remote repo: a new GitHub repository for the public engine

## Recommended Remote Setup

Create the GitHub repository as **empty**.

Do not pre-add:

- `README.md`
- `.gitignore`
- `LICENSE`

That avoids unrelated-history cleanup on first push.

## First-Time Connection

Open PowerShell and run:

```powershell
cd c:\SolverModule\public_kernel_solver_repo
git init
git add .
git commit -m "Initial public engine release"
git branch -M main
git remote add origin https://github.com/<your-name>/<your-repo>.git
git push -u origin main
```

## Check That It Worked

```powershell
git remote -v
git branch --show-current
git status
```

Expected:

- remote `origin` points to GitHub
- branch is `main`
- working tree is clean after the push

## Daily Update Flow

```powershell
cd c:\SolverModule\public_kernel_solver_repo
git status
git add .
git commit -m "Describe the change"
git push
```

## If The GitHub Repo Already Has Files

If the remote already has a README or license, the easiest fix is:

1. delete that GitHub repo
2. recreate it as an empty repo
3. run the first-time connection steps above

If you must keep the existing remote history, use:

```powershell
cd c:\SolverModule\public_kernel_solver_repo
git init
git branch -M main
git remote add origin https://github.com/<your-name>/<your-repo>.git
git fetch origin
git pull origin main --allow-unrelated-histories
```

Then resolve conflicts, commit, and push.

## Private Backend Note

Do not publish `private_backend_package` in the public repo.

Publish only the public interface folder unless you intentionally want a
private/internal repository for the private backend packaging flow.
