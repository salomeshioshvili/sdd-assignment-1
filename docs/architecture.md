```mermaid
flowchart TD
    Browser["Browser"] --> App["app.py: create_app() registers both blueprints"]
    subgraph LOG["Domain 1: log"]
        LR["log/routes.py: pages and forms"] --> LS["log/service.py: status rules, urgency, SQL"]
    end
    subgraph INS["Domain 2: insights"]
        IR["insights/routes.py: stats, checklist, reflections"] --> IS["insights/service.py: stats, skill gaps, checklist, SQL"]
    end
    App --> LR
    App --> IR
    IR -. "THE SEAM: list_hackathon_records()" .-> LS
    LR --> DB["db.py: connection, schema, seed"]
    IR --> DB
    DB --> File[("SQLite file: DATA_DIR/hackathon_journal.db")]
    linkStyle 5 stroke:#8b5cf6,stroke-width:3px
```

The dotted arrow is the seam. Insights imports exactly one thing from log: `list_hackathon_records()`, which returns a list of plain dictionaries (each with its projects and teammates, including the hackathon `id`). Log never imports insights.