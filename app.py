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
    st.session_state["active_tab"] = "Tâches"
if "reg_volunteer_name" not in st.session_state:
    st.session_state["reg_volunteer_name"] = ""
if "reg_meal_lunch" not in st.session_state:
    st.session_state["reg_meal_lunch"] = False
if "reg_meal_dinner" not in st.session_state:
    st.session_state["reg_meal_dinner"] = False
if "reg_comment" not in st.session_state:
    st.session_state["reg_comment"] = ""
if "task_title" not in st.session_state:
    st.session_state["task_title"] = ""
if "task_row_range" not in st.session_state:
    st.session_state["task_row_range"] = "1"
if "task_location_type" not in st.session_state:
    st.session_state["task_location_type"] = "Rangée(s)"


def parse_ranges(range_str: str):
    """
    Parse une chaîne de caractères représentant des rangs (ex: "1, 3-5, 7-9, 13")
    et retourne la liste triée des numéros de rangs uniques (bornés de 1 à 40).
    """
    rows = set()
    parts = range_str.replace(" ", "").split(",")
    for part in parts:
        if not part:
            continue
        if "-" in part:
            subparts = part.split("-")
            if len(subparts) == 2:
                try:
                    start = int(subparts[0])
                    end = int(subparts[1])
                    start = max(1, min(40, start))
                    end = max(1, min(40, end))
                    if start <= end:
                        rows.update(range(start, end + 1))
                    else:
                        rows.update(range(end, start + 1))
                except ValueError:
                    pass
        else:
            try:
                val = int(part)
                val = max(1, min(40, val))
                rows.add(val)
            except ValueError:
                pass
    return sorted(list(rows))


def add_registration_callback():
    event_id = st.session_state.get("reg_event")
    name = st.session_state.get("reg_volunteer_name", "").strip()
    meal_lunch = st.session_state.get("reg_meal_lunch", False)
    meal_dinner = st.session_state.get("reg_meal_dinner", False)
    comment = st.session_state.get("reg_comment", "").strip()
    
    if not name:
        st.error("Veuillez saisir le nom de l'intervenant.")
        return
    
    if name and event_id:
        try:
            supabase.table("registrations").insert({
                "event_id": event_id,
                "volunteer_name": name,
                "meal_lunch": meal_lunch,
                "meal_dinner": meal_dinner,
                "comment": comment if comment else None
            }).execute()
            st.success("Inscription réussie !")
            # Réinitialisation des champs du formulaire
            st.session_state.reg_volunteer_name = ""
            st.session_state.reg_meal_lunch = False
            st.session_state.reg_meal_dinner = False
            st.session_state.reg_comment = ""
        except Exception as e:
            st.error(f"Erreur lors de l'inscription : {e}")
            st.error(f"Erreur lors de l'inscription : {e}")


def add_task_callback():
    title = st.session_state.get("task_title", "").strip()
    range_str = st.session_state.get("task_row_range", "1").strip()
    location_type = st.session_state.get("task_location_type", "Rangée(s)")
    
    if not title:
        st.error("Veuillez saisir la description de la tâche.")
        return
    
    row_numbers = parse_ranges(range_str)
    if not row_numbers:
        st.error("Aucun numéro valide n'a été détecté (ex: 1, 3-5, 7).")
        return
    
    if location_type == "Interligne(s)":
        # Les interlignes sont stockés sous forme de nombres négatifs. L'interligne max est entre 39 et 40 (valeur -39).
        row_numbers = [-r for r in row_numbers if r < 40]
        if not row_numbers:
            st.error("Aucun numéro d'interligne valide n'a été détecté (doit être entre 1 et 39).")
            return
    
    try:
        payloads = [
            {
                "title": title,
                "row_number": row_num,
                "status": "À faire"
            }
            for row_num in row_numbers
        ]
        supabase.table("tasks").insert(payloads).execute()
        
        if location_type == "Interligne(s)":
            labels = [f"{abs(r)}-{abs(r)+1}" for r in row_numbers]
            st.success(f"{len(row_numbers)} tâche(s) ajoutée(s) avec succès pour les interlignes {', '.join(labels)} !")
        else:
            st.success(f"{len(row_numbers)} tâche(s) ajoutée(s) avec succès pour les rangs {row_numbers} !")
        # Réinitialisation des champs du formulaire
        st.session_state.task_title = ""
        st.session_state.task_row_range = "1"
        st.session_state.task_location_type = "Rangée(s)"
    except Exception as e:
        st.error(f"Erreur lors de l'ajout des tâches : {e}")


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
if col_tab1.button("📋 Tâches", use_container_width=True, type="primary" if st.session_state["active_tab"] == "Tâches" else "secondary"):
    st.session_state["active_tab"] = "Tâches"
    st.rerun()
if col_tab2.button("📅 Calendrier", use_container_width=True, type="primary" if st.session_state["active_tab"] == "Calendrier" else "secondary"):
    st.session_state["active_tab"] = "Calendrier"
    st.rerun()
if col_tab3.button("🛠️ Chantiers", use_container_width=True, type="primary" if st.session_state["active_tab"] == "Chantiers" else "secondary"):
    st.session_state["active_tab"] = "Chantiers"
    st.rerun()

st.markdown("---")

# ONGLET 1 : TÂCHES
if st.session_state["active_tab"] == "Tâches":
    st.header("Gestion des Tâches")
    
    st.subheader("Ajouter une tâche")
    with st.form("task_form"):
        st.text_input("Description de la tâche", key="task_title", placeholder="Ex: Épamprement, Taille, Palissage...")
        
        col_type, col_range = st.columns([1, 2])
        with col_type:
            st.radio("Type d'emplacement", options=["Rangée(s)", "Interligne(s)"], key="task_location_type", help="Sélectionnez si la tâche concerne directement des rangs de vigne ou l'espace entre deux rangs (interligne).")
        with col_range:
            st.text_input(
                "Numéro(s) (ex: 1, 3-5, 7, 9)", 
                key="task_row_range", 
                help="Saisissez des numéros uniques séparés par des virgules ou des plages avec un tiret.\n\n"
                     "- En mode **Rangée(s)** : '1, 3-5' créera des tâches pour les Rangs 1, 3, 4 et 5.\n"
                     "- En mode **Interligne(s)** : '1, 3-5' créera des tâches pour les interlignes entre 1 et 2, 3 et 4, 4 et 5, 5 et 6."
            )
            
        st.form_submit_button("Ajouter", on_click=add_task_callback)
        
    st.subheader("Liste des tâches")
    if tasks_data:
        df_tasks = pd.DataFrame(tasks_data)
        
        # Séparer les tâches "À faire" et les tâches "Faites"
        df_todo = df_tasks[df_tasks["status"] != "Fait"] if "status" in df_tasks.columns else pd.DataFrame()
        df_done = df_tasks[df_tasks["status"] == "Fait"] if "status" in df_tasks.columns else pd.DataFrame()
        
        # Options de localisation physique pour les listes de sélection
        location_options = []
        for r in range(1, 41):
            location_options.append((r, f"Rang {r}"))
            if r < 40:
                location_options.append((-r, f"Interligne {r}-{r+1}"))
        option_keys = [opt[0] for opt in location_options]

        # 1. Affichage des tâches "À faire" triées et groupées pour validation rapide
        st.markdown("### 📋 Tâches à faire")
        if not df_todo.empty:
            if "row_number" in df_todo.columns:
                # Tri physique : rang 1, puis interligne 1-2, puis rang 2, puis interligne 2-3, etc.
                df_todo["sort_key"] = df_todo["row_number"].apply(lambda r: 2 * r - 1 if r > 0 else 2 * abs(r))
                df_todo = df_todo.sort_values(by="sort_key")
            
            # On groupe les tâches à faire par leur titre (description)
            grouped_todo = df_todo.groupby("title")
            
            for title, group in grouped_todo:
                st.markdown(f"#### 🍇 {title}")
                
                # Construire la liste des options (task_id, label) pour ce groupe
                options = []
                for _, row in group.iterrows():
                    r_num = row["row_number"]
                    label = f"Rang {r_num}" if r_num > 0 else f"Interligne {abs(r_num)}-{abs(r_num)+1}"
                    options.append((row["id"], label))
                
                option_labels = [opt[1] for opt in options]
                option_map = {opt[1]: opt[0] for opt in options}
                
                # Formulaire de validation groupée compact en 3 colonnes
                col_sel, col_who, col_btn = st.columns([3.0, 1.8, 1.0])
                
                selected_labels = col_sel.multiselect(
                    f"Sélectionner les emplacements réalisés pour {title}",
                    options=option_labels,
                    default=[],
                    key=f"sel_{title}",
                    label_visibility="collapsed",
                    placeholder="Sélectionner les emplacements faits..."
                )
                
                who = col_who.text_input(
                    "Fait par", 
                    key=f"who_group_{title}", 
                    placeholder="Votre Prénom Nom", 
                    label_visibility="collapsed"
                )
                
                if col_btn.button("✓ Fait", key=f"btn_group_{title}", use_container_width=True):
                    if not who.strip():
                        st.error("Veuillez saisir le nom de l'intervenant pour valider.")
                    elif not selected_labels:
                        st.error("Veuillez sélectionner au moins un emplacement.")
                    else:
                        try:
                            # Récupérer les ids des tâches correspondantes
                            selected_ids = [option_map[lbl] for lbl in selected_labels]
                            for t_id in selected_ids:
                                supabase.table("tasks").update({
                                    "status": "Fait", 
                                    "completed_by": who.strip()
                                }).eq("id", t_id).execute()
                            st.success(f"{len(selected_ids)} tâche(s) validée(s) par {who} !")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur lors de la validation : {e}")
                
                # Affichage de la liste de tous les emplacements restants en dessous
                remaining_text = ", ".join(option_labels)
                st.markdown(f"<div style='font-size: 0.85rem; color: #666; margin-top: -10px; margin-bottom: 15px;'>📍 <b>Emplacements restants :</b> {remaining_text}</div>", unsafe_allow_html=True)
                st.markdown("<hr style='margin: 10px 0; border: none; border-top: 1px dashed #eee;'>", unsafe_allow_html=True)
        else:
            st.info("Toutes les tâches ont été réalisées ! 🎉")
            
        # 2. Affichage des tâches "Faites" triées par date, 10 dernières uniquement
        st.markdown("### ✅ Tâches terminées (10 dernières)")
        if not df_done.empty:
            if "created_at" in df_done.columns:
                df_done = df_done.sort_values(by="created_at", ascending=False)
            df_done_limited = df_done.head(10)
            
            for index, row in df_done_limited.iterrows():
                col_rang_val, col_desc, col_status, col_who = st.columns([2.0, 2.5, 1.0, 1.8])
                
                raw_row_num = row.get('row_number')
                old_row_num = int(raw_row_num) if pd.notna(raw_row_num) else 1
                
                try:
                    default_idx = option_keys.index(old_row_num)
                except ValueError:
                    default_idx = 0
                
                new_row_num = col_rang_val.selectbox(
                    "Emplacement",
                    options=location_options,
                    index=default_idx,
                    format_func=lambda x: x[1],
                    key=f"row_num_done_{row.get('id')}",
                    label_visibility="collapsed"
                )[0]
                
                if new_row_num != old_row_num:
                    try:
                        supabase.table("tasks").update({"row_number": new_row_num}).eq("id", row.get('id')).execute()
                        st.success("Emplacement mis à jour !")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur de modification de l'emplacement : {e}")
                
                col_desc.write(row.get('title', ''))
                col_status.markdown("<div style='padding-top: 5px; color: #2e7d32; font-weight: bold;'>🟢 Fait</div>", unsafe_allow_html=True)
                # Permet de modifier le nom en direct s'il y a eu une erreur de saisie
                old_name = row.get('completed_by') or 'Anonyme'
                new_name = col_who.text_input("Réalisé par", value=old_name, key=f"edit_{row.get('id')}", label_visibility="collapsed")
                if new_name != old_name:
                    try:
                        supabase.table("tasks").update({"completed_by": new_name.strip()}).eq("id", row.get('id')).execute()
                        st.success("Nom mis à jour !")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur de mise à jour : {e}")

        # 3. Section Gestion Avancée
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("🛠️ Gestion avancée et modifications individuelles"):
            st.markdown("##### Modifier l'emplacement ou supprimer des tâches en cours")
            if not df_todo.empty:
                for index, row in df_todo.iterrows():
                    col_edit_desc, col_edit_loc, col_edit_del = st.columns([3.0, 2.0, 1.0])
                    
                    col_edit_desc.write(f"**{row.get('title', '')}**")
                    
                    raw_row_num = row.get('row_number')
                    old_row_num = int(raw_row_num) if pd.notna(raw_row_num) else 1
                    
                    try:
                        default_idx = option_keys.index(old_row_num)
                    except ValueError:
                        default_idx = 0
                        
                    new_row_num = col_edit_loc.selectbox(
                        "Emplacement",
                        options=location_options,
                        index=default_idx,
                        format_func=lambda x: x[1],
                        key=f"edit_loc_todo_{row.get('id')}",
                        label_visibility="collapsed"
                    )[0]
                    
                    if new_row_num != old_row_num:
                        try:
                            supabase.table("tasks").update({"row_number": new_row_num}).eq("id", row.get('id')).execute()
                            st.success("Emplacement mis à jour !")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur de modification de l'emplacement : {e}")
                            
                    if col_edit_del.button("🗑️ Supprimer", key=f"del_todo_{row.get('id')}", use_container_width=True):
                        try:
                            supabase.table("tasks").delete().eq("id", row.get('id')).execute()
                            st.success("Tâche supprimée !")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur lors de la suppression : {e}")
            else:
                st.info("Aucune tâche en cours à modifier ou supprimer.")

    else:
        st.info("Aucune tâche répertoriée.")

    st.markdown("---")
    st.subheader("🏆 Activité du vignoble")
    if tasks_data:
        completed_tasks = [t for t in tasks_data if t.get("status") == "Fait" and t.get("completed_by")]
        if completed_tasks:
            worker_tasks = {}
            for t in completed_tasks:
                worker = t.get("completed_by").strip()
                title = t.get("title", "").strip()
                if worker not in worker_tasks:
                    worker_tasks[worker] = []
                if title and title not in worker_tasks[worker]:
                    worker_tasks[worker].append(title)
            
            recognition_data = [
                {"Intervenant": worker, "Tâches accomplies": ", ".join(tasks)}
                for worker, tasks in worker_tasks.items()
            ]
            df_recognition = pd.DataFrame(recognition_data)
            st.dataframe(df_recognition, use_container_width=True, hide_index=True)
        else:
            st.info("Aucune tâche n'a encore été réalisée pour figurer dans l'activité.")
    else:
        st.info("Aucune tâche disponible.")

# ONGLET 2 : CALENDRIER
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

# ONGLET 3 : CHANTIERS
elif st.session_state["active_tab"] == "Chantiers":
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
            
            # Deux checkboxes distinctes pour les repas du midi et du soir
            col_midi, col_soir = st.columns(2)
            col_midi.checkbox("Repas du MIDI requis", key="reg_meal_lunch")
            col_soir.checkbox("Repas du SOIR requis", key="reg_meal_dinner")
            
            # Saisie de commentaire libre (allergies, matériel...)
            st.text_input("Commentaire libre (ex: allergies, nourriture et matériel apporté, voiture dispo et trajets effectués...)", key="reg_comment")
            
            # Utilisation du callback pour l'inscription
            st.form_submit_button("S'inscrire", on_click=add_registration_callback)
            
        st.subheader("Récapitulatif des inscriptions")
        if registrations_data:
            df_events = pd.DataFrame(events_data)
            df_regs = pd.DataFrame(registrations_data)
            
            # Tolérance aux colonnes si le SQL de migration n'a pas encore été lancé
            if "meal_lunch" not in df_regs.columns:
                df_regs["meal_lunch"] = df_regs["needs_meal"] if "needs_meal" in df_regs.columns else False
            if "meal_dinner" not in df_regs.columns:
                df_regs["meal_dinner"] = False
            if "comment" not in df_regs.columns:
                df_regs["comment"] = ""
                
            # Filtrer les inscriptions associées à un événement valide
            df_regs_valid = df_regs[df_regs["event_id"].notna()]
            
            if not df_events.empty and not df_regs_valid.empty:
                # Jointure pour obtenir le nom de l'événement associé à l'inscription
                df_merged = pd.merge(df_regs_valid, df_events, left_on="event_id", right_on="id", suffixes=('_reg', '_event'))
                
                # S'assurer de la présence des colonnes dans le merge
                if "meal_lunch" not in df_merged.columns:
                    df_merged["meal_lunch"] = False
                if "meal_dinner" not in df_merged.columns:
                    df_merged["meal_dinner"] = False
                if "comment" not in df_merged.columns:
                    df_merged["comment"] = ""
                
                # --- AFFICHAGE DES GRANDS TOTALS GENERAUX ---
                total_lunch = int(df_merged["meal_lunch"].fillna(False).sum())
                total_dinner = int(df_merged["meal_dinner"].fillna(False).sum())
                total_people = int(df_merged["volunteer_name"].nunique())
                
                st.markdown("#### 📊 Cumul général des besoins")
                col_m1, col_m2, col_m3 = st.columns(3)
                col_m1.metric("👥 Intervenants uniques", total_people)
                col_m2.metric("🍽️ Repas MIDI totaux", total_lunch)
                col_m3.metric("🌙 Repas SOIR totaux", total_dinner)
                st.markdown("---")
                
                # --- AFFICHAGE DETAILE PAR EVENEMENT ---
                st.markdown("### 📅 Qui vient ? Suivi détaillé par Chantier")
                for _, event in df_events.iterrows():
                    event_id = event["id"]
                    event_title = event["title"]
                    event_date = event["start_date"]
                    
                    # Récupérer les inscriptions pour cet événement précis
                    event_regs = df_regs_valid[df_regs_valid["event_id"] == event_id]
                    
                    with st.expander(f"🛠️ {event_date} — {event_title} ({len(event_regs)} inscrit(s))", expanded=True):
                        if not event_regs.empty:
                            # Calcul des repas requis sur cet événement
                            evt_lunch = int(event_regs["meal_lunch"].fillna(False).sum())
                            evt_dinner = int(event_regs["meal_dinner"].fillna(False).sum())
                            
                            col_e1, col_e2 = st.columns(2)
                            col_e1.markdown(f"☀️ **Repas MIDI requis :** `{evt_lunch}`")
                            col_e2.markdown(f"🌙 **Repas SOIR requis :** `{evt_dinner}`")
                            
                            # Tableau de détail des inscrits de cet événement
                            df_evt_display = event_regs[["volunteer_name", "meal_lunch", "meal_dinner", "comment"]].copy()
                            df_evt_display["Repas Midi"] = df_evt_display["meal_lunch"].apply(lambda x: "Oui" if x else "Non")
                            df_evt_display["Repas Soir"] = df_evt_display["meal_dinner"].apply(lambda x: "Oui" if x else "Non")
                            df_evt_display["Commentaire"] = df_evt_display["comment"].fillna("")
                            
                            df_evt_display_clean = df_evt_display.rename(columns={
                                "volunteer_name": "Intervenant"
                            })[["Intervenant", "Repas Midi", "Repas Soir", "Commentaire"]]
                            
                            st.dataframe(df_evt_display_clean, use_container_width=True, hide_index=True)
                        else:
                            st.info("Aucun bénévole n'est inscrit sur ce chantier pour l'instant.")
            else:
                st.info("Aucune inscription associée à un chantier pour le moment.")
        else:
            st.info("Aucune inscription enregistrée dans la base de données.")
    else:
        st.warning("Aucun chantier configuré dans la table events. Créez des chantiers dans votre base Supabase (avec title, start_date et type).")