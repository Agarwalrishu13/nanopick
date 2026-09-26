<div align="center">

# nanoPick

**Find your files by saying what you remember.** No search operators, no index to build, no account.

*"A picture with receipt in the name, from last month."* Type the words you
remember, narrow it down by roughly what kind of thing it was and roughly when,
and the file appears — with a preview right on the page — ready to open, show
its folder, send a copy where it needs to go, or pack a few of them into one zip.

[![license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![python](https://img.shields.io/badge/python-3.9+-58a6ff.svg)]()
[![dependencies](https://img.shields.io/badge/required%20deps-0-f0883e.svg)]()
[![tests](https://img.shields.io/badge/tests-35%20passing-3ddc97.svg)]()

</div>

---

## What this is, in one paragraph

A lost file is never lost as a path — it is lost as a memory: *kind of a
picture, something like receipt, before the summer*. Every file manager wants
you to already know where it is. nanoPick turns the memory into the file: every
word you type must appear in the name (capitals do not matter, order does not
matter), you can keep only pictures or documents or music, only things from
this week or older than a year — and the answers say what a person checks
first: what it is, how long ago, how big, and which folder it lives in.

---

## Use it

1. Install Python if you do not have it — [python.org/downloads](https://www.python.org/downloads/).
2. Download this repo and unzip it.
3. **Windows:** double-click `run.bat`. **macOS / Linux:** `./run.sh`.
4. Your browser opens at `http://127.0.0.1:8779`.

<details>
<summary>Prefer the command line? (you do not need to)</summary>

```bash
python start.py                        # start and open the browser
python -m nanopick doctor              # say what this computer has, and stop
python -m nanopick --port 9000 --no-browser
```

</details>

---

## The four steps it walks you through

| step | what happens |
|---|---|
| **1. Say what you remember** | Any words from the name. Fewer words finds more. The page starts looking as you type. |
| **2. Narrow it down** | Pictures, documents, music, video, zips. Today, this week, this month, this year, older. Newest, biggest or by name. |
| **3. Click what looks right** | Pictures, songs, videos and text files show right there on the page. Everything else says so honestly. |
| **4. Do the thing** | Open it, show the folder it lives in, send a copy to your project folder, or tick a few and pack them into one zip. |

### Things it does that you would not expect from a toy

- **It never moves, renames or deletes anything.** "Send a copy" makes a copy;
  the original stays exactly where it was.
- **A copy never overwrites a copy.** The second one becomes
  `report (2).pdf`, exactly like a browser download would.
- **It only looks where you let it.** Your Desktop, Documents, Downloads,
  Pictures, Music and Videos by default — and you can change the list.
- **Previews cannot smuggle files out.** A file is only shown if it lives
  inside the folders nanoPick was allowed to look in — a made-up path gets a
  refusal, not the file.
- **Another website cannot drive it.** Every action checks that the request
  came from this app's own page on this computer.
- **The folder window is real.** Choosing where copies go opens your
  operating system's own folder picker.

---

## What it does not do, honestly

- **It does not look inside files.** It matches the *name* — a document whose
  name never mentions taxes will not come up for "taxes". That keeps the
  search instant and private: nothing is read, nothing is indexed, nothing to
  delete later.
- **It cannot play a PDF.** Documents get an honest "no preview for this
  kind" instead of a broken box.
- **It does not search the whole computer.** System folders and hidden swamps
  are skipped on purpose; add a folder to the list if your files live
  somewhere unusual.
- **There is no trash.** Nothing is deleted, so there is nothing to un-delete.

---

## Where your settings live

```
~/.nanopick/
  settings.json    the folders it may look in, where copies go, your last search
```

Delete that folder and nanoPick forgets everything. The files were never
stored there — only the memory of what you asked.

---

## The rest of the family

| app | what it is for |
|---|---|
| [nanoHome](https://github.com/Agarwalrishu13/nanohome) | one front door for every nano app on this computer |
| [nanoLaama](https://github.com/Agarwalrishu13/nanolaama) | talk to an AI on your own computer, offline |
| [nanoLearn](https://github.com/Agarwalrishu13/nanolearn) | drop a spreadsheet, get an answer machine |
| [nanoDoc](https://github.com/Agarwalrishu13/nanodoc) | drop in a document, ask it anything |
| [nanoSay](https://github.com/Agarwalrishu13/nanosay) | have anything read out loud |
| [nanoWrap](https://github.com/Agarwalrishu13/nanowrap) | the best-known programs, with ready-made buttons |
| [nanoShell](https://github.com/Agarwalrishu13/nanoshell) | any program at all, with words instead of flags |
| [nanoDesk](https://github.com/Agarwalrishu13/nanodesk) | every nano-style app you have, one click away |
| [nanoGit](https://github.com/Agarwalrishu13/nanogit) | your folder, kept safe without learning git |
| [nanoTune](https://github.com/Agarwalrishu13/nanotune) | your music, one page, no account |
| [nonoForge](https://github.com/Agarwalrishu13/nonoforge) | pick a card, press one button, you have an app |

---

MIT license. Made for people who do not write code, by someone who does.
