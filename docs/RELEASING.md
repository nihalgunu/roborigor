# Release checklist

## Going public (named repo)
1. Run the full test suite on py3.8 and py3.11; CI must be green.
2. `python scripts/check_paper_numbers.py` passes (regenerates numbers.tex and tables).
3. Squash the working history onto the `public-main` branch (one commit); force-push as `main`.
   Working-log commit messages are not part of the public record.
4. Verify no credentials: `git grep -iE "LAMBDA_API|HF_TOKEN|pypi-Ag|BEGIN.*KEY"` returns nothing.
5. Flip repository visibility to public.

## PyPI release (at submission)
1. Bump version in `pyproject.toml` (0.0.2.dev0 -> 0.1.0), build sdist+wheel, twine upload.
2. Token via TWINE_PASSWORD env var only; never in files.

## Before PaperPlaza upload (hard gates)
1. Anon footnote says the artifact accompanies the submission (no named URL); attach the artifact tarball as PaperPlaza supplementary material.
2. `\anontrue` is set; `pdftotext main.pdf` shows zero hits for the author name,
   handle, or package name; pdfinfo shows empty author/creator.
3. `python scripts/check_paper_numbers.py` green; page count <= 8.
4. Upload by Sep 12-13, not deadline day.

## Anonymized mirror (link this from the PDF, never the named repo)
1. Export the tree (no .git) and scrub, verifying zero hits for ALL of:
   nihal, gunukula, gmail, flowhelm, world-action-models, the GitHub handle.
   Known hit locations to rewrite: LICENSE copyright line, pyproject authors/urls,
   CITATION.cff, provenance docstrings mentioning the companion harness,
   docs/stage1-gate.md baseline path.
2. Re-run scripts/package_artifact.py identity scan over the mirror tree.
3. Upload to anonymous.4open.science; verify link renders logged out; put that URL in the PDF.
4. Do not update the mirror after the submission deadline.
