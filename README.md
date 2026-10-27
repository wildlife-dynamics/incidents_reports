# Incident Reports

An EarthRanger workflow that downloads **incidents** (ER's collections of related events, e.g. a poaching case made of an animal-carcass report and a poacher-spoor report) together with **all of their events**, and shows them as cases on a dashboard.

Nothing in it is partner-specific. You pick the data source and time range, and optionally group the dashboard into **one view per incident**.

## Dashboard

| Widget | Shows |
|---|---|
| No. of events | Events in the selected incidents |
| No. of incidents | Incidents in the time range |
| Events per incident | Average number of events per incident |
| Event types | Number of distinct event types |
| Map of incident events | Located events, coloured by event type, as ER icons or points (**Show event icons on the map**). Overlapping events get a count badge. When a view shows one incident, the legend is titled with it. |
| Events by event type | Horizontal bars, largest first, with count and share |
| Events by month | One bar per month (empty months kept), stacked by event type |
| Events by incident and event type | Sunburst: incidents inside (serial with a shortened title; full title on hover), their event types outside |
| Events by state, per incident | Table: New / Active / In review / Resolved / Total per incident, plus an "All incidents" row |
| Incident storyboards | Each incident (serial, title under it) as its ER event icons in time order, with the time between events on the arrows. Same-type events within 12 h share one tile (×N). Unlocated events are marked "no location". |
| Incident reports | One row per event, grouped by incident (merged incident cell: serial, title under it, and duration). Event (icon + serial: type), Title, Date, State, Priority, Location and Details by default; Category, Reported by, Notes, Created and Last updated can be added from the **Columns** menu. Long details open with "+N more". |

Every widget uses the same colour for an event type (most frequent type first; grey after 8 types).

Also written to the results folder: `incident_events.csv`, one row per event with its incident, listed in the desktop app's **Files** tab.

## Parameters

| Parameter | Notes |
|---|---|
| Data Source | EarthRanger connection |
| Time Range | Selects incidents by their own date. **All** of an incident's events are included, even those dated outside the range. Times are shown in the range's timezone. |
| Group by | Optional. **Incident** gives one dashboard view per incident. |
| Base Maps | Standard ecoscope base-map selector |
| Show event icons on the map | Checkbox, ticked by default: ER event icons; unticked: points coloured by event type |
| Default Columns | Reports-table columns shown before the viewer changes them |
| Show Event Icons | ER event icons in the reports table on/off |

## How it works

```
set_base_maps
get_incident_events            incidents in the range → their events by id (nested incidents followed),
                               display names, category, process_events_details, icons as data URIs
  → convert_values_to_timezone → assign_event_type_colors → persist_df (incident_events.csv)
  → split_groups (Incident, or AllGrouper)
      ├─ dataframe_column_nunique / events_per_incident → single-value widgets ─┐
      ├─ draw_incident_events_map → map widget                                   │ merge_widget_views
      ├─ draw_events_by_type_chart / _by_month_chart / draw_incident_sunburst    │
      └─ format_incident_state_table / _storyboards / _reports_table ────────────┴→ gather_dashboard
```

The new tasks are in [`ecoscope-workflows-ext-wd`](../wd-partner-tasks/src/ecoscope-workflows-ext-wd): `tasks/_incidents.py`, tested in `tests/tasks/test_incidents.py`. The KPI cards use the platform's own tasks (`dataframe_column_nunique`, `create_single_value_widget_single_view`); only `events_per_incident` is new.

Incidents inside incidents are followed up to 5 levels deep, and their events count towards the top-level incident. No site uses them yet, so this depth is fixed in `spec.yaml` (`max_depth: 5` on `incident_events`) and not shown in the form.

Incidents have no location of their own in ER. Maps use their events' locations; unlocated events appear only in the tables and storyboards.

## Local development

```bash
make dev                           # fast compile: cached env + ../wd-partner-tasks ext-wd installed editable
make run                           # run with param.yaml on real data → OUTPUT_DIR (default /tmp/incident-reports/output)
python3 dev/preview_dashboard.py /tmp/incident-reports/output   # dashboard.html using layout.json
make test CASE=wd-all-incidents    # app metadata + mock-IO CLI tests with snapshots
```

The editable ext-wd takes its version from wd-partner-tasks' git tags, so fetch them (`git fetch --tags`) or set `SETUPTOOLS_SCM_PRETEND_VERSION` to the version in `spec.yaml`. `make dev` output contains absolute local paths, so **don't commit it**, nor `wt-compiler-env-overrides.toml`.

| You change… | Run | Time |
|---|---|---|
| Task logic in ext-wd, or `param.yaml` | `make run` | no compile |
| `spec.yaml` task graph, task parameters, new tasks | `make dev` | ~10s |
| `spec.yaml` requirements, or a new dependency in ext-wd | `make dev` | ~30s (new cached env) |
| Want newer upstream package releases | `make dev-refresh` | ~20s |
| Ready to commit | stock `make recompile` | ~2–5 min |

Cached envs use ~2.5 GB each; clear them with `rm -rf ~/.cache/wt-dev-discovery`. Override `PARAM_FILE`, `OUTPUT_DIR`, etc. in `Makefile.local`.

### Test cases

| Case | Covers |
|---|---|
| `wd-all-incidents` | 4 incidents, 8 events; an event without a location, an event in review |
| `wd-by-incident` | Same data, one view per incident, icon map |
| `apnlosglaciares-glacier` | One resolved incident with 30 events over 10 months |
| `mep-2024` | 3 incidents, all events New |

The mock-IO data is in this repo, `mock-io/get-incident-events.example-return.parquet` (wd events, reporters anonymised), not in the ext-wd package. `make test` points wt-task at it through `WT_TASK_MOCK_IO__ECOSCOPE_WORKFLOWS_EXT_WD_TASKS_GET_INCIDENT_EVENTS`; set that variable yourself when running the generated tests directly. Mock runs need no EarthRanger connection.

Snapshots are in `__results_snapshots__/`. `test_otel_traces_success` currently fails: the generated workflow env has no `opentelemetry-sdk`, so no spans are written. That is the generated env, not the workflow.

### Releasing

`spec.yaml` takes ext-wd `0.0.9` from `https://repo.prefix.dev/ecoscope-workflows-custom/`. To ship task changes: merge them in wd-partner-tasks, tag `wd-vX.Y.Z` (the Publish action pushes it to prefix.dev), bump the ext-wd `version` in `spec.yaml` and `EXT_VERSION` in the `Makefile`, then run a stock `make recompile` and `make test`. Each stock recompile bumps `VERSION.yaml` (MIN + 1, or MAJ + 1 when the form parameters change).

To try unreleased task changes against the compiled workflow, `make build` builds `../wd-partner-tasks` into the local channel `/tmp/ecoscope-workflows-custom/release/artifacts/`; point the spec requirement there temporarily (and add the channel to `pixi.toml`), but don't commit that.
