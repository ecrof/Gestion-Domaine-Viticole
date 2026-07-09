import streamlit as st
import pandas as pd
import datetime
from supabase import create_client, Client

st.set_page_config(page_title="Gestion Domaine Viticole", layout="centered")

# 1 & 2. Initialisation du client Supabase
@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = get_supabase_client()

# 3. Initialisation de st.session_state pour vider les formulaires et éviter les doublons au rechargement
if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = "Chantiers"
if "reg_volunteer_name" not in st.session_state:
    st.session_state["reg_volunteer_name"] = ""
if "reg_needs_meal" not in st.session_state:
    st.session_state["reg_needs_meal"] = False
if "task_title" not in st.session_state:
    st.session_state["task_title"] = ""
if "task_row_number" not in st.session_state:
    st.session_state["task_row_number"] = 1


def add_registration_callback():
    event_id = st.session_state.get("reg_event")
    name = st.session_state.get("reg_volunteer_name", "").strip()
    meal = st.session_state.get("reg_needs_meal", False)
    
    if not name:
        st.error("Veuillez saisir le nom de l'intervenant.")
        return
    
    if name and event_id:
        try:
            supabase.table("registrations").insert({
                "event_id": event_id,
                "volunteer_name": name,
                "needs_meal": meal
            }).execute()
            st.success("Inscription réussie !")
            # Réinitialisation des champs du formulaire
            st.session_state.reg_volunteer_name = ""
            st.session_state.reg_needs_meal = False
        except Exception as e:
            st.error(f"Erreur lors de l'inscription : {e}")


def add_task_callback():
    title = st.session_state.get("task_title", "").strip()
    row = st.session_state.get("task_row_number", 1)
    
    if not title:
        st.error("Veuillez saisir la description de la tâche.")
        return
    
    if title:
        try:
            supabase.table("tasks").insert({
                "title": title,
                "row_number": row,
                "status": "À faire"
            }).execute()
            st.success("Tâche ajoutée avec succès !")
            # Réinitialisation des champs du formulaire
            st.session_state.task_title = ""
            st.session_state.task_row_number = 1
        except Exception as e:
            st.error(f"Erreur lors de l'ajout de la tâche : {e}")


def complete_task_callback(task_id, completed_by_name):
    if not completed_by_name.strip():
        st.error("Veuillez saisir le nom de l'intervenant pour valider la tâche.")
        return
    try:
        supabase.table("tasks").update({"status": "Fait", "completed_by": completed_by_name.strip()}).eq("id", task_id).execute()
        st.success(f"Tâche marquée comme faite par {completed_by_name} !")
    except Exception as e:
        st.error(f"Erreur lors de la mise à jour : {e}")


st.title("🍇 Gestion du Domaine Viticole")

# Récupération globale des données avec la syntaxe v2
try:
    events_data = supabase.table("events").select("*").execute().data
except Exception as e:
    st.error(f"Impossible de charger les événements : {e}")
    events_data = []

try:
    registrations_data = supabase.table("registrations").select("*").execute().data
except Exception as e:
    st.error(f"Impossible de charger les inscriptions : {e}")
    registrations_data = []

try:
    tasks_data = supabase.table("tasks").select("*").execute().data
except Exception as e:
    st.error(f"Impossible de charger les tâches : {e}")
    tasks_data = []


# 4. Navigation par onglets persistants
col_tab1, col_tab2, col_tab3 = st.columns(3)
if col_tab1.button("🛠️ Chantiers", use_container_width=True, type="primary" if st.session_state["active_tab"] == "Chantiers" else "secondary"):
    st.session_state["active_tab"] = "Chantiers"
    st.rerun()
if col_tab2.button("📋 Tâches", use_container_width=True, type="primary" if st.session_state["active_tab"] == "Tâches" else "secondary"):
    st.session_state["active_tab"] = "Tâches"
    st.rerun()
if col_tab3.button("📅 Calendrier", use_container_width=True, type="primary" if st.session_state["active_tab"] == "Calendrier" else "secondary"):
    st.session_state["active_tab"] = "Calendrier"
    st.rerun()

st.markdown("---")

# ONGLET 1 : CHANTIERS
if st.session_state["active_tab"] == "Chantiers":
    st.header("Chantiers et Inscriptions")
    
    if events_data:
        # Les événements possèdent 'title' et 'start_date' dans le schéma réel
        event_options = {e['id']: f"{e.get('start_date', 'Sans date')} - {e.get('title', 'Chantier')}" for e in events_data}
        
        st.subheader("S'inscrire à un chantier")
        with st.form("registration_form"):
            st.selectbox("Sélectionner un chantier", 
                         options=list(event_options.keys()), 
                         format_func=lambda x: event_options[x], 
                         key="reg_event")
            st.text_input("Nom de l'intervenant", key="reg_volunteer_name")
            st.checkbox("Repas requis (cocher si oui)", key="reg_needs_meal")
            
            # Utilisation du callback pour l'insertion
            st.form_submit_button("S'inscrire", on_click=add_registration_callback)
            
        st.subheader("Récapitulatif des inscriptions")
        if registrations_data:
            df_events = pd.DataFrame(events_data)
            df_regs = pd.DataFrame(registrations_data)
            
            # Filtrer les inscriptions associées à un événement valide
            df_regs_valid = df_regs[df_regs["event_id"].notna()]
            
            if not df_events.empty and not df_regs_valid.empty:
                # Jointure pour obtenir le nom de l'événement associé à l'inscription
                df_merged = pd.merge(df_regs_valid, df_events, left_on="event_id", right_on="id", suffixes=('_reg', '_event'))
                
                # Tableau récapitulatif : inscrits et repas par événement (les colonnes réelles de events sont 'title' et 'start_date')
                if "title_event" in df_merged.columns or "title" in df_merged.columns:
                    title_col = "title_event" if "title_event" in df_merged.columns else "title"
                    summary = df_merged.groupby(title_col).agg(
                        Inscrits=('volunteer_name', 'count'),
                        Repas_Prévus=('needs_meal', lambda x: int(x.fillna(False).sum()))
                    ).reset_index().rename(columns={
                        title_col: "Chantier",
                        "Inscrits": "Nombre d'inscrits",
                        "Repas_Prévus": "Repas requis"
                    })
                    
                    st.dataframe(summary, use_container_width=True, hide_index=True)
            else:
                st.info("Aucune inscription associée à un chantier pour le moment.")
        else:
            st.info("Aucune inscription enregistrée dans la base de données.")
    else:
        st.warning("Aucun chantier configuré dans la table events. Créez des chantiers dans votre base Supabase (avec title, start_date et type).")

# ONGLET 2 : TÂCHES
elif st.session_state["active_tab"] == "Tâches":
    st.header("Gestion des Tâches")
    
    st.subheader("Ajouter une tâche")
    with st.form("task_form"):
        st.text_input("Description de la tâche", key="task_title")
        st.number_input("Numéro de rang (1-40)", min_value=1, max_value=40, step=1, key="task_row_number")
        st.form_submit_button("Ajouter", on_click=add_task_callback)
        
    st.subheader("Liste des tâches")
    if tasks_data:
        df_tasks = pd.DataFrame(tasks_data)
        if "row_number" in df_tasks.columns:
            df_tasks = df_tasks.sort_values(by="row_number")
        
        for index, row in df_tasks.iterrows():
            col1, col2, col3, col4 = st.columns([3, 1, 1.5, 1])
            # La colonne réelle est 'title' pour la description, et 'row_number' pour le rang
            col1.write(f"**Rang {row.get('row_number', 'N/A')}** : {row.get('title', '')}")
            
            status = row.get("status", "À faire")
            if status == "Fait":
                col2.success("Fait")
                # Permet de modifier le nom en direct s'il y a eu une erreur de saisie
                old_name = row.get('completed_by') or 'Anonyme'
                new_name = col3.text_input("Réalisé par", value=old_name, key=f"edit_{row.get('id')}", label_visibility="collapsed")
                if new_name != old_name:
                    try:
                        supabase.table("tasks").update({"completed_by": new_name.strip()}).eq("id", row.get('id')).execute()
                        st.success("Nom mis à jour !")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur de mise à jour : {e}")
                col4.write("") 
            else:
                col2.warning("À faire")
                # Champ de saisie pour l'intervenant réalisateur de la tâche
                who = col3.text_input("Fait par", key=f"who_{row.get('id')}", placeholder="Prénom Nom", label_visibility="collapsed")
                # Bouton de validation pour changer le statut utilisant un callback
                col4.button("✓ Terminer", 
                            key=f"btn_done_{row.get('id')}", 
                            on_click=complete_task_callback, 
                            args=(row.get("id"), who))
    else:
        st.info("Aucune tâche répertoriée.")

    st.markdown("---")
    st.subheader("🏆 Classement d'activité du vignoble")
    if tasks_data:
        completed_tasks = [t for t in tasks_data if t.get("status") == "Fait" and t.get("completed_by")]
        if completed_tasks:
            leaderboard = {}
            for t in completed_tasks:
                worker = t.get("completed_by").strip()
                leaderboard[worker] = leaderboard.get(worker, 0) + 1
            
            df_leaderboard = pd.DataFrame([
                {"Contributeur": worker, "Tâches réalisées": count}
                for worker, count in leaderboard.items()
            ]).sort_values(by="Tâches réalisées", ascending=False)
            
            st.dataframe(df_leaderboard, use_container_width=True, hide_index=True)
        else:
            st.info("Aucune tâche n'a encore été réalisée pour alimenter le classement.")
    else:
        st.info("Aucune tâche disponible.")

# ONGLET 3 : CALENDRIER
elif st.session_state["active_tab"] == "Calendrier":
    st.header("Calendrier Viticole (Belgique)")
    
    # Récupération du mois en cours
    current_month = datetime.date.today().month
    
    MONTHS_FR = {
        1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril", 
        5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août", 
        9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
    }

    # Structure de données factuelle du cycle viticole belge
    calendar = [
        {
            "activity": "Taille", 
            "months": [1, 2, 3], 
            "tools": "Sécateur manuel/électrique (batteries chargées), scie passe-partout, gants anti-coupure."
        },
        {
            "activity": "Ébourgeonnage & Palissage", 
            "months": [4, 5], 
            "tools": "Gants légers, matériel d'attache, ceinture de maintien lombaire."
        },
        {
            "activity": "Écimage, Rognage & Débroussaillage", 
            "months": [6, 7], 
            "tools": "Cisaille, rogneuse, débroussailleuse, EPI complet (visière, casque anti-bruit)."
        },
        {
            "activity": "Effeuillage", 
            "months": [7, 8], 
            "tools": "Gants, lunettes de protection contre les sarments."
        },
        {
            "activity": "Vendanges", 
            "months": [8, 9, 10], 
            "tools": "Sécateur de vendange (épinette), seaux/paniers, bottes étanches, vêtements de pluie."
        },
        {
            "activity": "Vinification & Soutirage", 
            "months": [10, 11, 12], 
            "tools": "Matériel de vinification."
        },
        {
            "activity": "Repos hivernal & Entretien du matériel", 
            "months": [11, 12], 
            "tools": "Graisse, affûteuse, outils de maintenance mécanique."
        }
    ]
    
    # Séparation algorithmique selon le mois en cours
    current_activities = [item for item in calendar if current_month in item["months"]]
    activities = [item for item in calendar]
    
    # Affichage dynamique conditionnel
    st.subheader("Action(s) critique(s) ce mois-ci")
    
    if current_activities:
        for item in current_activities:
            st.error(f"⚠️ Période en cours : {item['activity']}")
            st.write(f"**Matériel requis :** {item['tools']}")
    else:
        st.info("Aucune activité viticole majeure répertoriée pour ce mois.")
        
    st.markdown("---")
    
    # Affichage statique du reste de l'année
    st.subheader("Planification annuelle")
    
    for item in activities:
        months_str = " - ".join([MONTHS_FR[m] for m in item["months"]])
        with st.expander(f"{item['activity']} ({months_str})"):
            st.write(f"**Période :** {months_str}")
            st.write(f"**Matériel :** {item['tools']}")