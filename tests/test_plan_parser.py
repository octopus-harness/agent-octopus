from agent_octopus.plan_parser import extract_plan_options, PlanOption


def test_extract_plan_options_format_a():
    text = """
## 🔱 ATUM — Egyptian Creator God

### Basic Profile
- Name: Atum (ID: 676)
- Pantheon: Egyptian

## ### Recommended Syncretica Plan

### 1. Cross-Cultural Creator God Comparative Analysis
The counterpart results reveal a strong "primordial creator god" archetype across traditions.

**Recommended Actions:**
- **`compute_clusters`** (target: "God", level: 5): Compute live vector clusters.
- **`create_cluster_snapshot`** (target: "God", level: 5, title: "Primordial Creator Gods"): Freeze clustering.

### 2. Detailed Cross-Pantheon Scholarly Report
Rigorously study auto-genesis.

**Recommended Actions:**
- **`create_cluster_report`** (cluster_snapshot_id: 123): 2-Phase report.

### 3. 3-Phase Hierarchical Deep Synthesis
Run monograph.

**Recommended Action:**
- **`generate_deep_synthesis`** (report_id: 456, batch_size: 5): 3-Phase monograph.

### 4. Specific Deity Pair Studies
- Atum <-> Svarog

### 5. Research Persistence
- Record findings using **`$$god_save_research`** or NoteKing integration.
"""
    options = extract_plan_options(text)
    assert len(options) == 5
    assert options[0].index == 1
    assert "Cross-Cultural Creator God" in options[0].title
    assert options[0].tool_name == "compute_clusters"
    assert "(target: \"God\", level: 5)" in options[0].action_text

    assert options[1].index == 2
    assert options[1].tool_name == "create_cluster_report"

    assert options[2].index == 3
    assert options[2].tool_name == "generate_deep_synthesis"

    assert options[4].index == 5
    assert options[4].tool_name == "$$god_save_research"


def test_extract_plan_options_format_b():
    text = """
Thematic Semantic Matches
1 Amun (Nubian) - Chief state deity
2 Ra (Egyptian) - Supreme sun god

Recommended Syncretica Plan

1. Cross-Pantheon Archetype Clustering
- Tool: compute_clusters, target_type='God', level=5-8, full_coverage=true
- Rationale: Atum's closest counterparts form a cluster.

2. Frozen Cluster Snapshot
- Tool: create_cluster_snapshot, target_type='God', level=6, title='Primordial Creator Gods'
- Rationale: Freezes the cluster.

3. Scholarly Map-Reduce Report
- Tool: create_cluster_report
- Rationale: Map-reduce report.

4. 3-Phase Hierarchical Monograph
- Tool: generate_deep_synthesis (after Phase 1 completes)
- Rationale: Hierarchical analysis.

5. Save the Research
- Tool: $$god_save_research
- Rationale: Save profile.

What changed:
- Stripped academic buzz
- Short sentences
"""
    options = extract_plan_options(text)
    assert len(options) == 5
    assert options[0].index == 1
    assert options[0].title == "Cross-Pantheon Archetype Clustering"
    assert options[0].tool_name == "compute_clusters"
    assert "target_type='God', level=5-8" in options[0].action_text

    assert options[1].index == 2
    assert options[1].tool_name == "create_cluster_snapshot"

    assert options[4].index == 5
    assert options[4].tool_name == "$$god_save_research"


def test_extract_plan_options_next_steps_and_actions():
    text = """
## 🔱 ATUM — Egyptian Creator God

### Recommended Next Steps & Actions

1. **Cross-Pantheon Counterparts**: `find_counterparts(entity_type='god', id=676, limit=10)` — Explore nearest vector neighbors across pantheons.
2. **Archetype Clustering**: `compute_clusters(target_type='God', level=5-8, full_coverage=false)` — Compute dynamic connected-components clusters.
3. **Freeze Cluster Snapshot**: `create_cluster_snapshot(target_type='God', level=6, title='Auto-Genesis Creator Deities')` — Freeze a catalog cluster snapshot.
4. **Map-Reduce Synthesis Report**: `create_cluster_report(cluster_snapshot_id=12, prompt='Analyze cross-cultural archetypes')` — Trigger a 2-Phase Map-Reduce scholarly report.
5. **Hierarchical Deep Synthesis**: `generate_deep_synthesis(report_id=12, batch_size=5)` — Run a 3-Phase monograph synthesis.
6. **Research Persistence**: `$$god_save_research` — Save findings and notes to NoteKing.
"""
    options = extract_plan_options(text)
    assert len(options) == 6
    assert options[0].index == 1
    assert options[0].title == "Cross-Pantheon Counterparts"
    assert options[0].tool_name == "find_counterparts"

    assert options[1].index == 2
    assert options[1].tool_name == "compute_clusters"

    assert options[2].index == 3
    assert options[2].tool_name == "create_cluster_snapshot"

    assert options[3].index == 4
    assert options[3].tool_name == "create_cluster_report"

    assert options[4].index == 5
    assert options[4].tool_name == "generate_deep_synthesis"

    assert options[5].index == 6
    assert options[5].tool_name == "$$god_save_research"


def test_extract_plan_options_empty_or_missing():
    assert extract_plan_options("") == []
    assert extract_plan_options("No plan here, just general text.") == []


def test_plan_selector_keybindings_and_toolbar():
    from unittest.mock import MagicMock
    from prompt_toolkit.buffer import Buffer
    from agent_octopus.tools import make_plan_key_bindings, make_plan_bottom_toolbar

    options = [
        PlanOption(1, "Step One", "tool1", "Execute step 1 using tool1", "1. Step One (tool1)"),
        PlanOption(2, "Step Two", "tool2", "Execute step 2 using tool2", "2. Step Two (tool2)"),
    ]
    state = {"selected_index": 0, "loaded": False, "dismissed": False}
    kb = make_plan_key_bindings(options, state)
    toolbar_fn = make_plan_bottom_toolbar(options, state)

    # 1. Test toolbar initial rendering
    html_out = toolbar_fn()
    assert html_out is not None
    assert "&gt; 1. Step One" in html_out.value

    # 2. Test Down arrow keybinding
    mock_event = MagicMock()
    mock_buf = MagicMock(spec=Buffer)
    mock_buf.text = ""
    mock_event.current_buffer = mock_buf

    down_handler = kb.get_bindings_for_keys(("down",))[0].handler
    down_handler(mock_event)
    assert state["selected_index"] == 1
    mock_event.app.invalidate.assert_called()

    # Verify toolbar updated highlight
    html_out_2 = toolbar_fn()
    assert "&gt; 2. Step Two" in html_out_2.value

    # 3. Test Up arrow circular wrap
    up_handler = kb.get_bindings_for_keys(("up",))[0].handler
    up_handler(mock_event)
    assert state["selected_index"] == 0

    # 4. Test Enter on empty buffer loads action_text
    from prompt_toolkit.keys import Keys
    enter_handler = kb.get_bindings_for_keys((Keys.ControlM,))[0].handler
    enter_handler(mock_event)
    mock_buf.insert_text.assert_called_once_with("Execute step 1 using tool1")
    assert state["loaded"] is True
    assert state["dismissed"] is True

    # 5. When dismissed, toolbar returns None
    assert toolbar_fn() is None

    # 6. Test Escape keybinding
    state["dismissed"] = False
    esc_handler = kb.get_bindings_for_keys((Keys.Escape,))[0].handler
    esc_handler(mock_event)
    assert state["dismissed"] is True
    assert toolbar_fn() is None


def test_extract_plan_options_wait_for_cluster_report():
    text = """
### Recommended Next Steps & Actions
1. **Map-Reduce Synthesis Report**: `create_cluster_report(cluster_snapshot_id=7, prompt='Analyze auto-genesis')` — Trigger report.
2. **Track Report Progress**: `wait_for_cluster_report(id=8, timeout_ms=600000)` — Poll report progress until complete.
"""
    options = extract_plan_options(text)
    assert len(options) == 2
    assert options[0].tool_name == "create_cluster_report"
    assert options[1].tool_name == "wait_for_cluster_report"
    assert options[1].index == 2
    assert "wait_for_cluster_report" in options[1].label
    assert "(id=8, timeout_ms=600000)" in options[1].action_text


def test_extract_plan_options_format_without_dots_or_bold():
    text = """
Recommended Next Steps & Actions

1 Archetype Clustering: compute_clusters(target_type='God', level=5, full_coverage=false) : Group these creator archetypes into connected-component clusters for structural analysis.
2 Freeze Cluster Snapshot: create_cluster_snapshot(target_type='God', level=6, title='Primordial Creator & Auto-genesis Archetypes') : Snapshot the creator deity cluster for reproducible scholarly tracking.
3 Map-Reduce Synthesis Report: create_cluster_report(cluster_snapshot_id=<id>, prompt='Compare auto-genesis creation narratives and primordial sovereignty across Egyptian, Mesoamerican, and African creator traditions.') : Generate a 2-Phase cross-cultural report.
4 Deep Synthesis Monograph: generate_deep_synthesis(report_id=<id>, batch_size=5) : Produce a 3-Phase hierarchical monograph synthesizing creator deity parallels.
5 Retrieve Full Profiles: get_god(id=<id>, include_myth=true) : Examine myth themes for specific counterparts like Marduk, Olodumare, or Ometeotl for detailed comparative analysis.
6 Research Persistence: $$god_save_research : Archive Atum's counterpart network and analysis notes to NoteKing for long-term reference.
"""
    options = extract_plan_options(text)
    assert len(options) == 6
    assert options[0].index == 1
    assert options[0].title == "Archetype Clustering"
    assert options[0].tool_name == "compute_clusters"
    assert options[0].raw_text == "1 Archetype Clustering: compute_clusters(target_type='God', level=5, full_coverage=false) : Group these creator archetypes into connected-component clusters for structural analysis."
    assert "(compute_clusters)" in options[0].label

    assert options[1].index == 2
    assert options[1].title == "Freeze Cluster Snapshot"
    assert options[1].tool_name == "create_cluster_snapshot"

    assert options[5].index == 6
    assert options[5].title == "Research Persistence"
    assert options[5].tool_name == "$$god_save_research"
    assert "$$god_save_research" in options[5].raw_text


def test_extract_plan_options_operational_next_steps_em_dash_multiline():
    text = """
Archetype Groups Discovered

The snapshot maps 1,021 deities into 110 connected-component clusters. Representative groups:

Cluster Group Shared Themes Size
Cosmic Order & Sky Domain Cosmic Order, Sky, Sovereignty, Fate 3
Creation & Benevolence Domain Creation, Benevolence, Light, Cosmic Balance 3

Atum (ID 676) sits within the 1,021 deities. His vector counterparts (Ptah, Ra, Amun, Khnum, and cross-cultural creators like Ölgün and Tengri) distribute across the relevant archetype groups.

Operational Next Steps

1 Synthesis Report — create_cluster_report(cluster_snapshot_id=10, prompt='Analyze the cross-cultural archetype of self-created primordial creator gods and their cosmogonic roles across 110 archetype clusters.')
  Generate a scholarly Map-Reduce report on creator deity theology across the full snapshot.
2 Deep Synthesis Monograph — generate_deep_synthesis(report_id=<report_id>, batch_size=5)
  Execute a 3-phase hierarchical deep synthesis after report completion.
3 Inspect Specific Clusters — get_cluster_group(id=<group_id>, include_members=true)
  Drill into individual cluster groups to verify deity pairings and Atum's specific neighbors.
4 View Snapshot Details — get_cluster_snapshot(id=10, include_groups=true, include_members=true)
  Pull the full breakdown to locate Atum's cluster and audit all member deities.
5 Compare with Myth Clustering — create_cluster_snapshot(target_type='Myth', level=6, title='Creator Myth Narratives Snapshot')
  Build a parallel myth-level snapshot to isolate creator narratives from deity profiles.
6 Research Persistence — $$god_save_research
  Archive findings on Atum's archetype clustering for future comparative mythology work.
"""
    options = extract_plan_options(text)
    assert len(options) == 6

    # Item 1
    assert options[0].index == 1
    assert options[0].title == "Synthesis Report"
    assert options[0].tool_name == "create_cluster_report"

    # Item 3: Inspect Specific Clusters
    assert options[2].index == 3
    assert options[2].title == "Inspect Specific Clusters"
    assert options[2].tool_name == "get_cluster_group"
    assert "id=<group_id>, include_members=true" in options[2].action_text
    assert "Drill into individual cluster groups" in options[2].raw_text
    assert options[2].raw_text.startswith("3 Inspect Specific Clusters — get_cluster_group")

    # Item 4: View Snapshot Details
    assert options[3].index == 4
    assert options[3].title == "View Snapshot Details"
    assert options[3].tool_name == "get_cluster_snapshot"

    # Item 6: Research Persistence
    assert options[5].index == 6
    assert options[5].title == "Research Persistence"
    assert options[5].tool_name == "$$god_save_research"


def test_extract_plan_options_cinderblock_domains():
    text = """
### Recommended Next Steps & Actions

1. **Astrophysical Counterparts**: `find_counterparts(entity_type='star_system', id=14, limit=10)` — Explore nearest vector neighbors across cosmic structures.
2. **Inspect Star System Profile**: `get_star_system(id=14, include_celestial_bodies=true)` — Retrieve full orbital and planet parameters.
3. **Inspect Organism Profile**: `get_organism(id=22)` — Retrieve ecological niche details.
4. **Inspect Molecule Profile**: `get_molecule(id=88, include_functional_groups=true)` — Retrieve chemical structure details.
5. **Inspect Particle Profile**: `get_subatomic_particle(id=7, include_quantum_states=true)` — Retrieve quantum state details.
6. **Inspect Country Profile**: `get_country(id=3, include_cities=true)` — Retrieve geopolitical profile.
7. **Save Astronomy Research**: `$$astronomer_save_research` — Archive star system findings to NoteKing.
8. **Save Biology Research**: `$$biologist_save_research` — Archive species findings to NoteKing.
9. **Save Chemistry Research**: `$$chemist_save_research` — Archive molecule findings to NoteKing.
10. **Save Physics Research**: `$$physicist_save_research` — Archive particle findings to NoteKing.
11. **Save Geopolitics Research**: `$$statesman_save_research` — Archive country findings to NoteKing.
"""
    options = extract_plan_options(text)
    assert len(options) == 11
    assert options[0].tool_name == "find_counterparts"
    assert options[1].tool_name == "get_star_system"
    assert options[2].tool_name == "get_organism"
    assert options[3].tool_name == "get_molecule"
    assert options[4].tool_name == "get_subatomic_particle"
    assert options[5].tool_name == "get_country"
    assert options[6].tool_name == "$$astronomer_save_research"
    assert options[7].tool_name == "$$biologist_save_research"
    assert options[8].tool_name == "$$chemist_save_research"
    assert options[9].tool_name == "$$physicist_save_research"
    assert options[10].tool_name == "$$statesman_save_research"


def test_known_cinderblock_tools_export_and_compatibility():
    from agent_octopus.plan_parser import (
        KNOWN_CINDERBLOCK_TOOLS,
        KNOWN_SYNCRETICA_TOOLS,
        COMMON_CINDERBLOCK_TOOLS,
        SYNCRETICA_TOOLS,
        ASTRONOMER_TOOLS,
        BIOLOGIST_TOOLS,
        CHEMIST_TOOLS,
        PHYSICIST_TOOLS,
        STATESMAN_TOOLS,
        RESEARCH_PERSISTENCE_COMMANDS,
    )

    # Verify alias identity
    assert KNOWN_SYNCRETICA_TOOLS is KNOWN_CINDERBLOCK_TOOLS

    # Verify all domain modular sets are present
    assert "compute_clusters" in COMMON_CINDERBLOCK_TOOLS
    assert "list_gods" in SYNCRETICA_TOOLS
    assert "list_star_systems" in ASTRONOMER_TOOLS
    assert "list_species" in BIOLOGIST_TOOLS
    assert "list_molecules" in CHEMIST_TOOLS
    assert "list_subatomic_particles" in PHYSICIST_TOOLS
    assert "list_countries" in STATESMAN_TOOLS
    assert "$$astronomer_save_research" in RESEARCH_PERSISTENCE_COMMANDS

    # Verify sorted by length descending
    for i in range(len(KNOWN_CINDERBLOCK_TOOLS) - 1):
        assert len(KNOWN_CINDERBLOCK_TOOLS[i]) >= len(KNOWN_CINDERBLOCK_TOOLS[i + 1])




