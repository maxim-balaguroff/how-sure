# how-sure

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24242389.svg)](https://doi.org/10.5281/zenodo.24242389)

English · [Русский](README.ru.md)

Small tools and notes from my work as a petroleum geologist. Each one deals with the same question: how sure are we, and what would make us surer?

Each tool is a single file that opens in a few seconds. The numbers are made up or come from open sources; nothing here comes from a client or an employer. A tool that calculates something ships with an example worked out by hand and built-in checks against it, so you can test the formulas before you trust them.

## Tools

| | Tool | What it does | Files |
|---|---|---|---|
| 01 | [Prediction vs. result](01-prediction-vs-result/) | Post-drill look-back. For every target: the prediction, what the bit found, the difference, its cause, and what changes in the next recommendation. Shows bias by group, how often your ± ranges held once chance is allowed for, and hits that were right for the wrong reason. | [Excel](https://github.com/maxim-balaguroff/how-sure/raw/main/01-prediction-vs-result/prediction-vs-result.xlsx) · PDF [EN](01-prediction-vs-result/prediction-vs-result-one-page.pdf) [RU](01-prediction-vs-result/prediction-vs-result-one-page.ru.pdf) |
| 02 | [Magnetic survey check](02-magnetic-survey-check/) | What must the survey resolve? Checks a planned magnetic survey before it is flown: for a dyke, a sill edge or a plug, does it stand above the noise, do two bodies show as two, how far apart can the lines be, and what changes between ground, low-clearance UAV, helicopter and fixed-wing heights. | [Open the page](https://maxim-balaguroff.github.io/how-sure/02-magnetic-survey-check/magnetic-survey-check.html) · [HTML](https://github.com/maxim-balaguroff/how-sure/releases/latest/download/magnetic-survey-check.html) |

[![Summary sheet of tool 01 on its made-up example](01-prediction-vs-result/screenshot-summary.png)](01-prediction-vs-result/)

## Using a tool

1. Download the file from its folder, or open the page in the browser.
2. Look at the checks first. With the example in place they read ALL PASS (tool 01, Test sheet: ALL 32 PASS; tool 02, bottom of the page: ALL 24 PASS).
3. Then put in your own numbers.

If a number looks wrong, please [open an issue](https://github.com/maxim-balaguroff/how-sure/issues).

## Licence and citation

Text and templates: [CC BY 4.0](LICENSE). Use them, change them, credit the source.

To cite: Balagurov, M. (2026). *how-sure: small tools and notes from a petroleum geologist's work* (v1.1). Zenodo. [https://doi.org/10.5281/zenodo.24242389](https://doi.org/10.5281/zenodo.24242389). The DOI always points to the latest version; the *Cite this repository* button gives other formats.

Built with AI assistance; the geology and the checks are mine.

Maxim Balagurov · [LinkedIn](https://www.linkedin.com/in/balagurov)
