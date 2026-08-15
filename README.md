# AX Wars Archive

AX Wars was a time-bounded build sprint in which three independent AI products were developed from public-information case studies. The project established a shared method: define the operational bottleneck, narrow the scope, separate language-model judgment from deterministic controls, and build an evaluation harness capable of changing the design.

The original monorepo and plugin marketplace are no longer maintained. Development continues in separate canonical repositories with English documentation, independent installation, testing, and licensing boundaries.

## Current repositories

| Product | Canonical repository | Primary evidence |
| --- | --- | --- |
| GAAP–IFRS Suite | [bridgewright/gaap-ifrs-suite](https://github.com/bridgewright/gaap-ifrs-suite) | Deterministic conversion, grounded retrieval, and 177 original evaluation tests |
| Regulatory Incident Response | [bridgewright/regulatory-incident-response](https://github.com/bridgewright/regulatory-incident-response) | 25 automated tests, 14 legal scenarios, and eight reconstructed public incidents |
| Alfboard | [bridgewright/alfboard](https://github.com/bridgewright/alfboard) | Voice-led stakeholder discovery with deterministic schema validation |

The portfolio-level narrative is available at [AX Verse](https://github.com/bridgewright/ax-verse).

## Archive status

- Historical commit identifiers changed when third-party accounting-standard corpus files were removed from public history.
- The legacy `axwars` marketplace has been retired. Use the installation instructions in each canonical repository.
- Accounting-standard text is not distributed. The GAAP–IFRS Suite provides ingestion software and requires users to supply material they are legally entitled to use.
- Company and product names in the history identify public-information case studies and do not imply affiliation or endorsement.

This repository is retained to preserve the origin and development context of the work. It is not the source for current installation or maintenance.
