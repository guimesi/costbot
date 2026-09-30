"""Input cards that edit lists in session_state (equipment, scope items).

They are st.fragments with on_click callbacks: adding or removing an item
reruns only the card, never the whole page, and no st.rerun() is needed.
"""
import streamlit as st

from costbot.constants import EQUIPMENT_TYPES_52, _PROCESS_EQUIPMENT

SCOPE_ITEM_TYPES = ['process_unit', 'osbl', 'pipeline_segment', 'storage', 'marine', 'infrastructure']


def _add_equipment():
    eq_type = st.session_state.eq_type
    count = int(st.session_state.eq_count)
    for item in st.session_state.equipment_items:
        if item['type'] == eq_type:      # merge instead of duplicating the row
            item['count'] += count
            return
    st.session_state.equipment_items.append({'type': eq_type, 'count': count})


def _remove_equipment(i):
    st.session_state.equipment_items.pop(i)


def _add_scope_item():
    name = (st.session_state.si_facility or '').strip()
    if name:
        st.session_state.scope_items.append({'type': st.session_state.si_type, 'facility_type': name})
        st.session_state.si_facility = ''


def _remove_scope_item(i):
    st.session_state.scope_items.pop(i)


@st.fragment
def equipment_card(core_ready: bool, border: bool = True):
    """`border=False` drops the card frame and title for hosts that already
    frame it (an expander in Proposta A, a sidebar group in Proposta B)."""
    with st.container(border=border):
        if border:
            st.markdown("**:material/precision_manufacturing: Equipment list**")
            st.caption("Unlocks the equipment vector model, the best broad model (66% within ±30%). "
                       "Pumps, exchangers, towers, drums, compressors: even rough counts help.")
        process_types = sorted(_PROCESS_EQUIPMENT)
        other_types = sorted(set(EQUIPMENT_TYPES_52) - _PROCESS_EQUIPMENT)
        with st.container(horizontal=True, vertical_alignment="bottom"):
            st.selectbox("Equipment type", process_types + other_types, key="eq_type",
                         disabled=not core_ready, help="Process equipment first; valves, instruments and "
                         "electrical items are ignored by the model on purpose.")
            st.number_input("Count", min_value=1, value=1, key="eq_count", disabled=not core_ready, width=110)
            st.button("Add", icon=":material/add:", key="eq_add", on_click=_add_equipment, disabled=not core_ready)
        items = st.session_state.equipment_items
        if items:
            with st.container(gap=None):
                for i, eq in enumerate(items):
                    with st.container(horizontal=True, vertical_alignment="center"):
                        st.markdown(f"{eq['type']} × **{eq['count']}**", width="stretch")
                        st.button("Remove", icon=":material/close:", key=f"eqrm_{i}", type="tertiary",
                                  on_click=_remove_equipment, args=(i,))
        else:
            st.caption("No equipment added yet.")


@st.fragment
def scope_items_card(core_ready: bool, border: bool = True):
    with st.container(border=border):
        if border:
            st.markdown("**:material/view_list: Scope items**")
            st.caption("Build the project from pieces (a process unit, an OSBL package, a pipeline segment). "
                       "Each piece is matched against the chip library and summed.")
        with st.container(horizontal=True, vertical_alignment="bottom"):
            st.selectbox("Scope item type", SCOPE_ITEM_TYPES, key="si_type", disabled=not core_ready,
                         format_func=lambda x: x.replace('_', ' ').capitalize())
            st.text_input("Facility name", placeholder="e.g. Crude unit, Utilities", key="si_facility",
                          disabled=not core_ready)
            st.button("Add", icon=":material/add:", key="si_add", on_click=_add_scope_item, disabled=not core_ready)
        items = st.session_state.scope_items
        if items:
            with st.container(gap=None):
                for i, item in enumerate(items):
                    with st.container(horizontal=True, vertical_alignment="center"):
                        st.markdown(f"{item['type'].replace('_', ' ')}: **{item['facility_type']}**", width="stretch")
                        st.button("Remove", icon=":material/close:", key=f"rm_{i}", type="tertiary",
                                  on_click=_remove_scope_item, args=(i,))
        else:
            st.caption("No scope items added yet.")
