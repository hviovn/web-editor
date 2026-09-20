# web-editor

Flask dictionary editor backed by the `db` folder of [`kreier/timeline`](https://github.com/kreier/timeline).

## GitHub Pages

The repository includes a GitHub Actions workflow that clones the timeline repository during the build, generates a static version of the editor, and deploys it to:

<https://hviovn.github.io/web-editor/>

Run the workflow with a push to `main` or manually from the **Actions** tab. GitHub Pages serves static files, so the Pages version stores edits in the browser's `localStorage` and downloads edited dictionaries; it cannot run the Flask server or write back to GitHub automatically. The full Flask version remains available for local use.

## Local Flask server

```bash
python -m pip install flask pandas
git clone https://github.com/kreier/timeline.git
python flask/web-editor.py
```

The Flask app clones or refreshes a timeline checkout in `workfolder/timeline`. Override it with `TIMELINE_REPO_URL` and `TIMELINE_WORK_DIR` when needed.
