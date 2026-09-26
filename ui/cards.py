"""Input cards that edit lists in session_state (equipment, scope items).

They are st.fragments with on_click callbacks: adding or removing an item
reruns only the card, never the whole page, and no st.rerun() is needed.
"""
import streamlit as st

from costbot.constants import EQUIPMENT_TYPES_52, _PROCESS_EQUIPMENT

_OTHER_FACILITY = '__other__'


def _add_equipment():
    st.session_state.equipment_items.append(
        {'type': st.session_state.eq_type, 'count': int(st.session_state.eq_count)}
    )


def _remove_equipment(i):
    st.session_state.equipment_items.pop(i)


def _add_scope_item():
    name = (st.session_state.si_facility or '').strip()
    if name:
        st.session_state.scope_items.append(
            {'type': st.session_state.si_type, 'facility_type': name}
        )
        st.session_state.si_facility = ''


def _remove_scope_item(i):
    st.session_state.scope_items.pop(i)


# Cards 2 and 5 are fragments: adding or removing a list item reruns only the
# card, not the whole page (the full-page rerun was the "page reload" users saw
# on slower connections). Callbacks mutate session_state before the rerun, so
# no explicit rerun call is needed.
@st.fragment
def equipment_card(core_ready: bool):
    st.markdown("#### 2. Equipment List (EquipmentVector)")
    st.caption("Best broad model (66% ±30%). What major equipment is involved?")
    with st.expander("Add equipment for vector-based estimate",
                     expanded=bool(st.session_state.equipment_items)):
        eq_col1, eq_col2 = st.columns(2)
        with eq_col1:
            process_types = sorted(_PROCESS_EQUIPMENT)
            other_types = sorted(set(EQUIPMENT_TYPES_52) - _PROCESS_EQUIPMENT)
            st.selectbox("Equipment Type", process_types + other_types, key="eq_type")
        with eq_col2:
            st.number_input("Count", min_value=1, value=1, key="eq_count")
        st.button("+ Add Equipment", disabled=not core_ready, on_click=_add_equipment, key="eq_add")

    for i, eq in enumerate(st.session_state.equipment_items):
        cols = st.columns([4, 1])
        with cols[0]:
            st.markdown(f"**{eq['type']}** x {eq['count']}")
        with cols[1]:
            st.button("X", key=f"eqrm_{i}", on_click=_remove_equipment, args=(i,))


@st.fragment
def scope_items_card(core_ready: bool):
    st.markdown("#### 5. Scope Items (Composite)")
    with st.expander("Add scope items for composite estimate", expanded=False):
        si_col1, si_col2 = st.columns(2)
        with si_col1:
            st.selectbox(
                "Scope Type",
                ['process_unit', 'osbl', 'pipeline_segment', 'storage', 'marine', 'infrastructure'],
                key="si_type",
            )
        with si_col2:
            st.text_input("Facility Name", placeholder="e.g. Crude Unit, Utilities", key="si_facility")
        st.button("+ Add Scope Item", disabled=not core_ready, on_click=_add_scope_item, key="si_add")

    for i, item in enumerate(st.session_state.scope_items):
        cols = st.columns([4, 1])
        with cols[0]:
            st.markdown(f"**{i+1}.** {item['type']} - {item['facility_type']}")
        with cols[1]:
            st.button("X", key=f"rm_{i}", on_click=_remove_scope_item, args=(i,))
