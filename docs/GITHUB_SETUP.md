# GitHub setup (one person does this once)

## 1. Create the repo
- github.com -> New repository. Name: `sidechannel-repair`. Private is fine; the supervisor and reviewers can be added later.
- Do NOT tick "Add a README / .gitignore / licence" (the zip already has them).

## 2. Push the first commit
```
unzip sidechannel-repair.zip && cd sidechannel-repair
git init -b main
git add .
git commit -m "Initial repo structure with interfaces and Stage 3/4 skeleton"
git remote add origin https://github.com/<your-username>/sidechannel-repair.git
git push -u origin main
```
Then create the stage branches:
```
git branch stage1-detect && git branch stage2-verify && git branch stage3-4-repair
git push origin stage1-detect stage2-verify stage3-4-repair
```

## 3. Repo settings
- Settings -> Collaborators: add all five teammates (Write access).
- Settings -> Branches -> add rule for `main`: require a pull request before merging, require 1 approval, block force pushes.
- Settings -> General -> Pull Requests: tick "Automatically delete head branches".
- Settings -> Secrets and variables -> Actions: put API keys here if CI ever needs them. Never in code.
- Add the supervisor and both reviewers as read-only collaborators if they ask for access.

## 4. Daily workflow
```
git checkout stage3-4-repair
git pull
# ...work, commit often...
git push
```
Open a pull request into `main` when a piece works. Pull `main` into your branch regularly so integration problems show up early.

## 5. Dropping a finished stage in
Duo 1 / Duo 2 replace the body of `run()` in their stage file, keep the signature and output format, and open a PR. Then run `python -m pipeline.run ...` on `main` to see the real stages working together.
