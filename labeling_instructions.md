# How to fill in gold_standard_labels_TO_FILL.csv

## What this is for
We built an automated system that groups research papers by which optimization problem they're actually about (e.g. two papers both testing "Rastrigin" should be grouped together, even if worded differently). Before trusting that automated grouping, we need to check it against real human judgment — that's this file.

## What to do
Open the CSV in Excel or Google Sheets. There are 40 rows, each one research paper.

1. **Read these columns for each row:** `Paper_Title`, `Problem_Context`, `Benchmark_Name`, `Target_Landscape`. Together they describe what problem that paper is actually about.

2. **Ask yourself: "have I already seen this same problem in an earlier row?"**
   - **Yes** → put the exact same label in `entity_id` as that earlier row (e.g. `g1`)
   - **No, it's new** → give it a new label (`g2`, `g3`, ...)
   - Simplest method: just go top to bottom, numbering new problems as you find them and reusing a number when you spot a repeat.

3. **If you're genuinely unsure**, type `uncertain` in `entity_id`. Don't guess — an honest "unsure" is more useful than a wrong guess, and it won't count against either side when we score this.

4. **Use the `notes` column** for anything worth remembering, e.g. "same suite as row 15, just worded differently" or "not sure if this single function counts as the same problem as the whole suite it's part of."

## A worked example (from the real data, to make the task unambiguous)
Rows for `ZDT1`, `ZDT2`, and `ZDT3` — these look similar by name, but they are three genuinely different problems (different mathematical properties). The standard answer here is three different `entity_id` labels, not one. If your instinct is to group them together, stop and think about whether they're really the same problem, not just similarly named.

## Important — please do this independently
Don't discuss your answers with teammates while labeling, and don't look at anyone else's file while working. If more than one person is labeling, everyone should get their own fresh copy of the same CSV and label it separately, then we compare afterward. This independence is the entire point — it's what makes this a real check rather than just people agreeing with each other's guesses.

## When you're done
Save the file as exactly: `gold_standard_labels.csv`
Send it back — that exact filename is already wired into our validation script, so it can be scored immediately with no extra steps.

## How long this takes
Roughly 1.5–2 hours for one person doing all 40 rows carefully. If split across two people (each doing their own full independent pass, not dividing the rows), budget the same per person, plus a short discussion afterward to compare where you disagreed.
