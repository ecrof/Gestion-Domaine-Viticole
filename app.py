import streamlit as st
import pandas as pd
import datetime
import requests
import calendar as cal_lib
from supabase import create_client, Client

st.set_page_config(page_title="Gestion Domaine Viticole", layout="centered")

# 1 & 2. Initialisation du client Supabase
@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = get_supabase_client()

@st.cache_data(ttl=3600)  # Cache weather for 1 hour
def fetch_weather():
    url = "https://api.open-meteo.com/v1/forecast?latitude=50.65&longitude=4.26&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=Europe/Brussels&forecast_days=14"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return None

def get_weather_info(code):
    if code == 0:
        return "☀️", "Soleil"
    elif code in [1, 2]:
        return "⛅", "Éclaircies"
    elif code == 3:
        return "☁️", "Couvert"
    elif code in [45, 48]:
        return "🌫️", "Brouillard"
    elif code in [51, 53, 55, 56, 57]:
        return "🌧️", "Bruine"
    elif code in [61, 63, 65, 66, 67]:
        return "🌧️", "Pluie"
    elif code in [71, 73, 75, 77]:
        return "❄️", "Neige"
    elif code in [80, 81, 82]:
        return "🌦️", "Averses"
    elif code in [95, 96, 99]:
        return "⛈️", "Orage"
    else:
        return "❓", "Inconnu"

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


st.title("🍇 Gestion du Domaine Viticole du petit Chaumont")

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
            
        # 2. Affichage des tâches "Faites" triées par date, groupées de manière compacte
        st.markdown("### ✅ Tâches terminées récentes")
        if not df_done.empty:
            if "created_at" in df_done.columns:
                df_done["sort_key"] = df_done["row_number"].apply(lambda r: 2 * r - 1 if r > 0 else 2 * abs(r))
                # On trie d'abord par date de complétion décroissante, puis par emplacement physique
                df_done = df_done.sort_values(by=["created_at", "sort_key"], ascending=[False, True])
            
            # Prendre les 20 dernières tâches faites pour ne pas surcharger, puis grouper
            df_done_limited = df_done.head(20)
            
            # Groupement par description de tâche (title)
            grouped_done = df_done_limited.groupby("title")
            
            for title, group in grouped_done:
                st.markdown(f"**🍇 {title}**")
                
                # Sous-groupement par intervenant
                worker_groups = group.groupby("completed_by")
                
                for worker, w_group in worker_groups:
                    locations = []
                    for _, row in w_group.iterrows():
                        r_num = row["row_number"]
                        label = f"Rang {r_num}" if r_num > 0 else f"Interligne {abs(r_num)}-{abs(r_num)+1}"
                        locations.append(label)
                    
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;👤 **{worker}** : {', '.join(locations)}")
                st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px dotted #eee;'>", unsafe_allow_html=True)
        else:
            st.info("Aucune tâche terminée pour le moment.")

        # 3. Section Gestion Avancée
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("🛠️ Gestion avancée et modifications individuelles"):
            tab_edit_todo, tab_edit_done = st.tabs(["📋 Tâches en cours", "✅ Tâches terminées"])
            
            with tab_edit_todo:
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
                                r_err = f"Erreur lors de la suppression : {e}"
                                st.error(r_err)
                else:
                    st.info("Aucune tâche en cours à modifier ou supprimer.")
                    
            with tab_edit_done:
                st.markdown("##### Modifier ou réinitialiser des tâches terminées (20 dernières)")
                if not df_done.empty:
                    df_done_edit_list = df_done.head(20)
                    for index, row in df_done_edit_list.iterrows():
                        col_ed_desc, col_ed_loc, col_ed_who, col_ed_revert, col_ed_del = st.columns([2.0, 1.8, 1.8, 1.2, 1.0])
                        
                        col_ed_desc.write(f"**{row.get('title', '')}**")
                        
                        raw_row_num = row.get('row_number')
                        old_row_num = int(raw_row_num) if pd.notna(raw_row_num) else 1
                        
                        try:
                            default_idx = option_keys.index(old_row_num)
                        except ValueError:
                            default_idx = 0
                            
                        new_row_num = col_ed_loc.selectbox(
                            "Emplacement",
                            options=location_options,
                            index=default_idx,
                            format_func=lambda x: x[1],
                            key=f"edit_loc_done_{row.get('id')}",
                            label_visibility="collapsed"
                        )[0]
                        
                        if new_row_num != old_row_num:
                            try:
                                supabase.table("tasks").update({"row_number": new_row_num}).eq("id", row.get('id')).execute()
                                st.success("Emplacement mis à jour !")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erreur de modification de l'emplacement : {e}")
                                
                        old_name = row.get('completed_by') or 'Anonyme'
                        new_name = col_ed_who.text_input(
                            "Réalisé par", 
                            value=old_name, 
                            key=f"edit_who_done_{row.get('id')}", 
                            label_visibility="collapsed"
                        )
                        if new_name != old_name:
                            try:
                                supabase.table("tasks").update({"completed_by": new_name.strip()}).eq("id", row.get('id')).execute()
                                st.success("Nom mis à jour !")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erreur de mise à jour : {e}")
                                
                        if col_ed_revert.button("↩️ À faire", key=f"revert_done_{row.get('id')}", use_container_width=True, help="Remettre cette tâche au statut 'À faire'"):
                            try:
                                supabase.table("tasks").update({"status": "À faire", "completed_by": None}).eq("id", row.get('id')).execute()
                                st.success("Tâche remise à faire !")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erreur lors du retour en arrière : {e}")
                                
                        if col_ed_del.button("🗑️ Supprimer", key=f"del_done_{row.get('id')}", use_container_width=True):
                            try:
                                supabase.table("tasks").delete().eq("id", row.get('id')).execute()
                                st.success("Tâche supprimée !")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erreur lors de la suppression : {e}")
                else:
                    st.info("Aucune tâche terminée à modifier.")

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
    
    MONTHS_FR = {
        1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril", 
        5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août", 
        9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
    }
    
    # 1. Météo de Ittre (Belgique) - Récupération et parsing
    weather_data = fetch_weather()
    weather_by_date = {}
    if weather_data and "daily" in weather_data:
        daily = weather_data["daily"]
        times = daily.get("time", [])
        codes = daily.get("weathercode", [])
        t_maxs = daily.get("temperature_2m_max", [])
        t_mins = daily.get("temperature_2m_min", [])
        precips = daily.get("precipitation_sum", [])
        
        for i, t_str in enumerate(times):
            code = codes[i] if i < len(codes) else 0
            t_max = t_maxs[i] if i < len(t_maxs) else 0
            t_min = t_mins[i] if i < len(t_mins) else 0
            precip = precips[i] if i < len(precips) else 0
            
            emoji, desc = get_weather_info(code)
            weather_by_date[t_str] = {
                "emoji": emoji,
                "desc": desc,
                "temp": f"{int(t_min)}°-{int(t_max)}°",
                "precip": f"{precip}mm" if precip > 0 else ""
            }

    # 2. Récupération globale des disponibilités et ouverture dans Supabase
    db_ready = True
    calendar_status = {}
    presences_by_date = {}
    
    try:
        cal_data = supabase.table("vignoble_calendar").select("*").execute().data
        for c in cal_data:
            calendar_status[c["date"]] = {
                "is_open": c["is_open"],
                "note": c.get("note") or ""
            }
    except Exception as e:
        db_ready = False
        st.warning("⚠️ Les tables SQL de gestion du calendrier n'ont pas encore été initialisées dans Supabase. "
                   "Veuillez exécuter les commandes SQL de configuration (voir ci-dessous) dans l'éditeur de requêtes SQL de Supabase.")
        with st.expander("📝 Afficher le code SQL à copier-coller dans Supabase", expanded=True):
            st.code("""
-- 1. Table pour gérer l'ouverture du vignoble par date
CREATE TABLE IF NOT EXISTS public.vignoble_calendar (
    date DATE PRIMARY KEY,
    is_open BOOLEAN NOT NULL DEFAULT false,
    note TEXT
);

-- 2. Table pour gérer les présences des bénévoles
CREATE TABLE IF NOT EXISTS public.vignoble_presences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL REFERENCES public.vignoble_calendar(date) ON DELETE CASCADE,
    volunteer_name TEXT NOT NULL,
    comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    CONSTRAINT unique_date_volunteer UNIQUE (date, volunteer_name)
);

-- RLS (Sécurité)
ALTER TABLE public.vignoble_calendar ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.vignoble_presences ENABLE ROW LEVEL SECURITY;

-- Politiques de lecture/écriture publique (clé anonyme)
CREATE POLICY "Allow public read on calendar" ON public.vignoble_calendar FOR SELECT USING (true);
CREATE POLICY "Allow public insert on calendar" ON public.vignoble_calendar FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public update on calendar" ON public.vignoble_calendar FOR UPDATE USING (true);
CREATE POLICY "Allow public delete on calendar" ON public.vignoble_calendar FOR DELETE USING (true);

CREATE POLICY "Allow public read on presences" ON public.vignoble_presences FOR SELECT USING (true);
CREATE POLICY "Allow public insert on presences" ON public.vignoble_presences FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public update on presences" ON public.vignoble_presences FOR UPDATE USING (true);
CREATE POLICY "Allow public delete on presences" ON public.vignoble_presences FOR DELETE USING (true);
            """, language="sql")
            
    if db_ready:
        try:
            pres_data = supabase.table("vignoble_presences").select("*").execute().data
            for p in pres_data:
                d_str = p["date"]
                vol = p["volunteer_name"]
                if d_str not in presences_by_date:
                    presences_by_date[d_str] = []
                if vol not in presences_by_date[d_str]:
                    presences_by_date[d_str].append(vol)
        except Exception as e:
            st.error(f"Erreur lors du chargement des présences : {e}")

    # 3. Formulaires de saisie et de configuration
    today = datetime.date.today()
    current_month_num = today.month
    current_year_num = today.year
    
    next_month_num = current_month_num + 1 if current_month_num < 12 else 1
    next_year_num = current_year_num if current_month_num < 12 else current_year_num + 1
    
    _, max_day_in_next_month = cal_lib.monthrange(next_year_num, next_month_num)
    max_date = datetime.date(next_year_num, next_month_num, max_day_in_next_month)
    
    st.subheader("🗓️ Présences et Météo (Ittre)")
    
    if db_ready:
        col_form_adm, col_form_vol = st.columns(2)
        
        with col_form_adm:
            with st.expander("⚙️ Ouvrir/Fermer le vignoble (Gestionnaire)", expanded=False):
                with st.form("open_close_form"):
                    adm_date = st.date_input("Date à configurer", min_value=today, max_value=max_date, value=today, key="adm_date")
                    adm_status = st.selectbox("État du vignoble", ["Ouvert pour bénévoles", "Fermé"], index=0)
                    adm_note = st.text_input("Note/Activité (ex: Vendanges, Désherbage...)", placeholder="Optionnel")
                    
                    submitted_adm = st.form_submit_button("Enregistrer l'état", use_container_width=True)
                    if submitted_adm:
                        date_str = adm_date.isoformat()
                        is_open_val = (adm_status == "Ouvert pour bénévoles")
                        try:
                            # Upsert logic
                            existing = supabase.table("vignoble_calendar").select("date").eq("date", date_str).execute().data
                            if existing:
                                supabase.table("vignoble_calendar").update({
                                    "is_open": is_open_val,
                                    "note": adm_note.strip() if adm_note.strip() else None
                                }).eq("date", date_str).execute()
                            else:
                                supabase.table("vignoble_calendar").insert({
                                    "date": date_str,
                                    "is_open": is_open_val,
                                    "note": adm_note.strip() if adm_note.strip() else None
                                }).execute()
                            st.success(f"Vignoble configuré comme {'OUVERT' if is_open_val else 'FERMÉ'} pour le {date_str} !")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur de configuration : {e}")
                            
        with col_form_vol:
            # Let's get list of dates that are actually open
            open_dates_list = sorted([d for d, status in calendar_status.items() if status["is_open"] and datetime.date.fromisoformat(d) >= today])
            
            with st.expander("🙋 S'inscrire pour venir aider (Bénévole)", expanded=False):
                if not open_dates_list:
                    st.info("Aucun jour d'ouverture n'est planifié pour le moment. Revenez bientôt !")
                else:
                    with st.form("presence_form_cal_new"):
                        vol_name = st.text_input("Votre nom", placeholder="Prénom Nom", key="new_vol_name")
                        date_sel_str = st.selectbox("Date de votre venue", options=open_dates_list, format_func=lambda x: f"{datetime.date.fromisoformat(x).strftime('%d/%m/%Y')} — {calendar_status[x]['note'] or 'Ouvert'}")
                        
                        col_action_vol_1, col_action_vol_2 = st.columns(2)
                        sub_coming = col_action_vol_1.form_submit_button("Je viens aider 🟢", use_container_width=True)
                        sub_cancel = col_action_vol_2.form_submit_button("Me retirer ❌", use_container_width=True)
                        
                        if sub_coming:
                            if not vol_name.strip():
                                st.error("Veuillez saisir votre nom.")
                            else:
                                try:
                                    supabase.table("vignoble_presences").insert({
                                        "date": date_sel_str,
                                        "volunteer_name": vol_name.strip()
                                    }).execute()
                                    st.success("Inscription enregistrée ! Merci pour votre aide ! 🍇")
                                    st.rerun()
                                except Exception as e:
                                    if "unique" in str(e).lower() or "23505" in str(e):
                                        st.info("Vous êtes déjà inscrit pour ce jour là.")
                                    else:
                                        st.error(f"Erreur d'inscription : {e}")
                                        
                        if sub_cancel:
                            if not vol_name.strip():
                                st.error("Veuillez saisir votre nom.")
                            else:
                                try:
                                    supabase.table("vignoble_presences").delete().eq("date", date_sel_str).eq("volunteer_name", vol_name.strip()).execute()
                                    st.success("Retrait enregistré.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erreur lors du retrait : {e}")

    # 4. Affichage des calendriers mensuels sous forme d'onglets
    tab_curr, tab_nxt = st.tabs([f"📅 {MONTHS_FR[current_month_num]} {current_year_num}", f"📅 {MONTHS_FR[next_month_num]} {next_year_num}"])
    
    def render_month_calendar(year, month):
        cols = st.columns(7)
        days_of_week = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
        for i, d_name in enumerate(days_of_week):
            cols[i].markdown(f"<div style='text-align: center; font-weight: bold; background-color: #f0f2f6; padding: 5px; border-radius: 3px; font-size: 0.8rem;'>{d_name}</div>", unsafe_allow_html=True)
        
        weeks = cal_lib.monthcalendar(year, month)
        for week in weeks:
            cols = st.columns(7)
            for i, day_num in enumerate(week):
                if day_num == 0:
                    cols[i].markdown("<div style='min-height: 50px;'></div>", unsafe_allow_html=True)
                else:
                    date_obj = datetime.date(year, month, day_num)
                    date_str = date_obj.isoformat()
                    
                    # Déterminer le statut d'ouverture
                    day_status = calendar_status.get(date_str, {"is_open": False, "note": ""})
                    is_open = day_status["is_open"]
                    note = day_status["note"]
                    
                    status_html = ""
                    bg_color = "#ffffff"
                    border_color = "#eee"
                    
                    if is_open:
                        bg_color = "#eef9ee"
                        border_color = "#81c784"
                        status_html = f"<div style='color: #2e7d32; font-size: 0.75rem; font-weight: bold; text-align: center; background-color: #c8e6c9; border-radius: 3px; padding: 2px 4px; margin-bottom: 3px;'>🔓 OUVERT</div>"
                        if note:
                            status_html += f"<div style='font-size: 0.7rem; text-align: center; color: #111; font-weight: bold; margin-bottom: 3px;'>📢 {note}</div>"
                    else:
                        status_html = f"<div style='color: #757575; font-size: 0.7rem; text-align: center; margin-bottom: 3px;'>🔒 Fermé</div>"
                        if note:
                            status_html += f"<div style='font-size: 0.65rem; text-align: center; color: #757575; font-style: italic; margin-bottom: 3px;'>📝 {note}</div>"
                    
                    # Météo
                    weather = weather_by_date.get(date_str, None)
                    weather_html = ""
                    if weather:
                        weather_html = f"<div style='font-size: 0.75rem; text-align: center; margin-top: 2px;'>{weather['emoji']} {weather['temp']}</div>"
                        if weather['precip']:
                            weather_html += f"<div style='font-size: 0.7rem; text-align: center; color: #1f77b4;'>💧 {weather['precip']}</div>"
                    
                    # Présences (uniquement pour les jours ouverts)
                    presence_html = ""
                    if is_open:
                        vols = presences_by_date.get(date_str, [])
                        if vols:
                            presence_html += f"<div style='color: #1b5e20; font-size: 0.7rem; font-weight: bold; text-align: center; line-height: 1.1; margin-top: 4px;'>🙋 {', '.join(vols)}</div>"
                        else:
                            presence_html += f"<div style='color: #757575; font-size: 0.65rem; text-align: center; font-style: italic; margin-top: 4px;'>Aucun inscrit</div>"
                    
                    # Mise en évidence du jour en cours
                    if date_obj == today:
                        bg_color = "#fff9c4"
                        border_color = "#fbc02d"
                    
                    cols[i].markdown(
                        f"<div style='background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 5px; padding: 4px; min-height: 90px; margin-bottom: 4px; overflow: hidden;'>"
                        f"<div style='font-weight: bold; font-size: 0.8rem; text-align: right; color: #333;'>{day_num}</div>"
                        f"{status_html}"
                        f"{weather_html}"
                        f"{presence_html}"
                        f"</div>", 
                        unsafe_allow_html=True
                    )
   
    with tab_curr:
        render_month_calendar(current_year_num, current_month_num)
    with tab_nxt:
        render_month_calendar(next_year_num, next_month_num)
        
    st.markdown("---")

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