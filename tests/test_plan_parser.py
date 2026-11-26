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


