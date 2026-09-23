# oglink — MUIOGO's OG-CLEWS linker

Couples a solved CLEWS case into an OG-Core country model: it reads the CLEWS results, turns the
electricity price and related signals into OG-Core inputs, runs the country model, and reports the
macroeconomic result with a run manifest.

The linker runs in **its own environment**. MUIOGO never imports it; it launches it as a separate
process. The linker in turn launches each OG country model in that model's own environment, and gives
it this package's source folder for the length of the run. Nothing is installed into the country
model's environment.

This package was brought in from the research repository ogclews-link (branch
`experiment/v18-gold-coupled`, commit `ee92c9b`). New work on the linker happens here.
