import streamlit as st
import random
import math
from collections import defaultdict

# =============== Вспомогательные функции ===============

def get_preferred_color(player, color_history, current_round, total_rounds):
    history = color_history[player]
    if len(history) >= 2 and history[-1] == history[-2]:
        if current_round < total_rounds:
            return 'Ч' if history[-1] == 'Б' else 'Б'
    white_count = history.count('Б')
    black_count = history.count('Ч')
    if white_count < black_count:
        return 'Б'
    elif black_count < white_count:
        return 'Ч'
    else:
        if not history:
            return 'Б'
        return 'Ч' if history[-1] == 'Б' else 'Б'

def decide_colors(p1, p2, color_history, current_round, total_rounds):
    pref1 = get_preferred_color(p1, color_history, current_round, total_rounds)
    pref2 = get_preferred_color(p2, color_history, current_round, total_rounds)
    if pref1 == 'Б' and pref2 == 'Б':
        w1 = color_history[p1].count('Б')
        w2 = color_history[p2].count('Б')
        return (p1, p2) if w1 <= w2 else (p2, p1)
    elif pref1 == 'Ч' and pref2 == 'Ч':
        w1 = color_history[p1].count('Б')
        w2 = color_history[p2].count('Б')
        return (p2, p1) if w1 >= w2 else (p1, p2)
    elif pref1 == 'Б':
        return (p1, p2)
    else:
        return (p2, p1)

def generate_round_robin_schedule(players, rounds_needed):
    """Генерация расписания кругового турнира."""
    if not players or rounds_needed <= 0:
        return []
    players = players[:]
    n = len(players)
    is_odd = (n % 2 == 1)
    if is_odd:
        players.append("BYE")
        n += 1

    base_rounds = n - 1
    full_schedule = []
    current = players[:]

    for r in range(base_rounds):
        pairs = []
        for i in range(n // 2):
            p1 = current[i]
            p2 = current[n - 1 - i]
            if p1 == "BYE":
                pairs.append((None, p2))
            elif p2 == "BYE":
                pairs.append((p1, None))
            else:
                pairs.append((p1, p2))
        full_schedule.append(pairs)
        current = [current[0]] + [current[-1]] + current[1:-1]

    if rounds_needed > base_rounds:
        second_circle = []
        for pairs in full_schedule:
            new_pairs = []
            for p1, p2 in pairs:
                if p1 is None or p2 is None:
                    new_pairs.append((p1, p2))
                else:
                    new_pairs.append((p2, p1))  # меняем цвета во втором круге
            second_circle.append(new_pairs)
        full_schedule.extend(second_circle)

    return full_schedule[:rounds_needed]

def assign_colors_round_robin(pairs, white_count, bye_count, color_history):
    """Назначает цвета с учётом BYE и записывает в историю."""
    new_pairs = []
    for p1, p2 in pairs:
        if p1 is None or p2 is None:
            new_pairs.append((p1, p2))
        else:
            w1, w2 = white_count[p1], white_count[p2]
            b1, b2 = bye_count[p1], bye_count[p2]
            if w1 < w2:
                white, black = p1, p2
            elif w2 < w1:
                white, black = p2, p1
            else:
                if b1 > b2:
                    white, black = p2, p1
                elif b2 > b1:
                    white, black = p1, p2
                else:
                    white, black = (p1, p2) if p1 < p2 else (p2, p1)
            # Записываем в историю цветов
            color_history[white].append('Б')
            color_history[black].append('Ч')
            white_count[white] += 1
            new_pairs.append((white, black))
    return new_pairs

def initial_pairing_with_colors(players, color_history, current_round, total_rounds):
    random.shuffle(players)
    pairs = []
    for i in range(0, len(players) - 1, 2):
        white, black = decide_colors(players[i], players[i+1], color_history, current_round, total_rounds)
        pairs.append((white, black))
    bye = players[-1] if len(players) % 2 == 1 else None
    return pairs, bye

def swiss_pairing_with_colors(players, scores, played_pairs, bye_history, color_history, current_round, total_rounds):
    n = len(players)
    is_odd = (n % 2 == 1)
    sorted_players = sorted(players, key=lambda x: (-scores[x], random.random()))
    paired = set()
    pairs = []

    for max_diff in [0.5, 1.0, float('inf')]:
        for i, p1 in enumerate(sorted_players):
            if p1 in paired:
                continue
            opponent = None
            for p2 in sorted_players[i+1:]:
                if p2 in paired:
                    continue
                if frozenset({p1, p2}) in played_pairs:
                    continue
                if abs(scores[p1] - scores[p2]) <= max_diff:
                    opponent = p2
                    break
            if opponent:
                white, black = decide_colors(p1, opponent, color_history, current_round, total_rounds)
                pairs.append((white, black))
                paired.add(p1)
                paired.add(opponent)
                played_pairs.add(frozenset({p1, opponent}))

    unpaired = [p for p in players if p not in paired]
    bye = None

    if is_odd:
        if len(unpaired) == 1:
            bye = unpaired[0]
        elif len(unpaired) > 1:
            unpaired_sorted = sorted(unpaired, key=lambda x: (scores[x], random.random()))
            candidates = [p for p in unpaired_sorted if p not in bye_history]
            if not candidates:
                candidates = unpaired_sorted
            bye = candidates[0]
            others = [p for p in unpaired if p != bye]
            random.shuffle(others)
            for i in range(0, len(others) - 1, 2):
                a, b = others[i], others[i+1]
                if frozenset({a, b}) not in played_pairs:
                    white, black = decide_colors(a, b, color_history, current_round, total_rounds)
                    pairs.append((white, black))
                    played_pairs.add(frozenset({a, b}))
    else:
        if len(unpaired) > 0:
            st.warning(f"Не удалось спарить всех игроков в туре {current_round}.")
    return pairs, bye

def calculate_buchholz(players, scores, opponents):
    buchholz = {}
    for p in players:
        total = sum(scores[opp] for opp in opponents[p])
        buchholz[p] = total
    return buchholz

# =============== Основное приложение ===============

st.set_page_config(page_title="Шахматный турнир", layout="wide")
st.title("♟️ Шахматный турнир")

if "players_data" not in st.session_state:
    st.session_state.players_data = []
if "show_nat_rating" not in st.session_state:
    st.session_state.show_nat_rating = False
if "show_fide_rating" not in st.session_state:
    st.session_state.show_fide_rating = False
if "show_fshr_id" not in st.session_state:
    st.session_state.show_fshr_id = False
if "show_fide_id" not in st.session_state:
    st.session_state.show_fide_id = False
if "default_rating" not in st.session_state:
    st.session_state.default_rating = 1000

if "initialized" not in st.session_state:
    st.session_state.initialized = False
    st.session_state.players = []
    st.session_state.scores = {}
    st.session_state.opponents = defaultdict(list)
    st.session_state.played_pairs = set()
    st.session_state.bye_history = set()
    st.session_state.total_rounds = 0
    st.session_state.current_round = 0
    st.session_state.tournament_type = ""
    st.session_state.round_robin_schedule = []
    st.session_state.tour_data = {}
    st.session_state.completed = False
    st.session_state.ratings = {}
    st.session_state.color_history = defaultdict(list)
    st.session_state.white_count = defaultdict(int)
    st.session_state.bye_count = defaultdict(int)

# =============== Вкладки ===============
if not st.session_state.initialized:
    tabs = st.tabs(["Игроки и рейтинги", "Туры"])
    
    # =============== Вкладка 1: Игроки и рейтинги ===============
    with tabs[0]:
        st.subheader("Игроки")

        with st.expander("Дополнительная информация", expanded=False):
            st.markdown("Выберите, какие поля отображать:")
            cols = st.columns(2)
            with cols[0]:
                show_nat_rating = st.checkbox("Рейтинг ФШР", value=st.session_state.show_nat_rating)
                show_fshr_id = st.checkbox("ID ФШР", value=st.session_state.show_fshr_id)
            with cols[1]:
                show_fide_rating = st.checkbox("Рейтинг ФИДЕ", value=st.session_state.show_fide_rating)
                show_fide_id = st.checkbox("ID ФИДЕ", value=st.session_state.show_fide_id)
            
            if st.button("Применить"):
                st.session_state.show_nat_rating = show_nat_rating
                st.session_state.show_fide_rating = show_fide_rating
                st.session_state.show_fshr_id = show_fshr_id
                st.session_state.show_fide_id = show_fide_id
                st.rerun()

        show_rating_fields = st.session_state.show_nat_rating or st.session_state.show_fide_rating
        if show_rating_fields:
            st.session_state.default_rating = st.number_input(
                "Рейтинг по умолчанию",
                value=st.session_state.default_rating,
                min_value=0,
                step=1,
                help="Будет использован для пустых рейтингов."
            )

        for i, player in enumerate(st.session_state.players_data):
            with st.container():
                st.markdown(f"**Игрок {i+1}**")
                cols = st.columns([3, 3, 1])
                with cols[0]:
                    last_name = st.text_input("Фамилия", value=player["last_name"], key=f"last_{i}")
                    if last_name.strip() == "":
                        st.markdown('<span style="color:red;font-size:0.9em">Обязательно</span>', unsafe_allow_html=True)
                with cols[1]:
                    first_name = st.text_input("Имя", value=player["first_name"], key=f"first_{i}")
                    if first_name.strip() == "":
                        st.markdown('<span style="color:red;font-size:0.9em">Обязательно</span>', unsafe_allow_html=True)
                with cols[2]:
                    if st.button("🗑️", key=f"del_{i}", help="Удалить игрока"):
                        st.session_state.players_data.pop(i)
                        st.rerun()
                
                any_extra = (st.session_state.show_nat_rating or 
                            st.session_state.show_fide_rating or 
                            st.session_state.show_fshr_id or 
                            st.session_state.show_fide_id)
                
                if any_extra:
                    widths = []
                    if st.session_state.show_nat_rating: widths.append(2)
                    if st.session_state.show_fide_rating: widths.append(2)
                    if st.session_state.show_fshr_id: widths.append(1)
                    if st.session_state.show_fide_id: widths.append(1)
                    
                    if widths:
                        extra_cols = st.columns(widths)
                        idx = 0
                        fields = {}
                        if st.session_state.show_nat_rating:
                            fields["nat_rating"] = st.text_input("Рейтинг ФШР", value=str(player["nat_rating"]) if player["nat_rating"] != "" else "", key=f"nat_{i}")
                            idx += 1
                        if st.session_state.show_fide_rating:
                            fields["fide_rating"] = st.text_input("Рейтинг ФИДЕ", value=str(player["fide_rating"]) if player["fide_rating"] != "" else "", key=f"fide_{i}")
                            idx += 1
                        if st.session_state.show_fshr_id:
                            fields["fshr_id"] = st.text_input("ID ФШР", value=player["fshr_id"], key=f"fshr_{i}")
                            idx += 1
                        if st.session_state.show_fide_id:
                            fields["fide_id"] = st.text_input("ID ФИДЕ", value=player["fide_id"], key=f"fid_{i}")
                        
                        st.session_state.players_data[i] = {
                            "last_name": last_name,
                            "first_name": first_name,
                            "nat_rating": fields.get("nat_rating", ""),
                            "fide_rating": fields.get("fide_rating", ""),
                            "fshr_id": fields.get("fshr_id", ""),
                            "fide_id": fields.get("fide_id", "")
                        }
                else:
                    st.session_state.players_data[i] = {
                        "last_name": last_name,
                        "first_name": first_name,
                        "nat_rating": "", "fide_rating": "",
                        "fshr_id": "", "fide_id": ""
                    }
                st.divider()

        st.button("➕ Добавить игрока", on_click=lambda: st.session_state.players_data.append({
            "last_name": "", "first_name": "",
            "nat_rating": "", "fide_rating": "",
            "fshr_id": "", "fide_id": ""
        }))

    # =============== Вкладка 2: Туры ===============
    with tabs[1]:
        valid_players = [p for p in st.session_state.players_data if p["last_name"].strip() and p["first_name"].strip()]
        n_players = len(valid_players)

        if n_players < 2:
            st.warning("Добавьте хотя бы двух игроков на вкладке «Игроки и рейтинги».")
        else:
            st.info(f"Участников: {n_players}")
            total_rounds = None
            tournament_type = None

            if n_players < 7:
                tournament_type = st.radio("Выберите тип турнира:", ["Один круг", "Два круга"], index=0)
                if tournament_type == "Один круг":
                    total_rounds = n_players if n_players % 2 == 1 else n_players - 1
                else:
                    base = n_players if n_players % 2 == 1 else n_players - 1
                    total_rounds = 2 * base
            else:
                tournament_type = st.radio("Выберите тип турнира:", ["Один круг", "Два круга", "Швейцарская система"], index=2)
                if tournament_type == "Один круг":
                    total_rounds = n_players if n_players % 2 == 1 else n_players - 1
                elif tournament_type == "Два круга":
                    base = n_players if n_players % 2 == 1 else n_players - 1
                    total_rounds = 2 * base
                else:
                    recommended = math.ceil(math.log2(n_players)) + 2
                    max_circle = n_players if n_players % 2 == 1 else n_players - 1
                    max_swiss = min(max_circle - 1, recommended + 2)
                    min_swiss = recommended
                    if min_swiss > max_swiss:
                        min_swiss = max_swiss
                    total_rounds = st.slider("Количество туров:", min_swiss, max_swiss, recommended)

            if st.button("Начать турнир", type="primary"):
                errors = []
                for i, p in enumerate(st.session_state.players_data):
                    if not p["last_name"].strip(): errors.append(f"У игрока {i+1} не указана фамилия.")
                    if not p["first_name"].strip(): errors.append(f"У игрока {i+1} не указано имя.")
                if errors:
                    for err in errors: st.error(err)
                elif tournament_type is None:
                    st.error("Выберите тип турнира.")
                else:
                    players_list = []
                    ratings_dict = {}
                    default_rating = st.session_state.default_rating
                    show_rating_fields = st.session_state.show_nat_rating or st.session_state.show_fide_rating

                    for p in st.session_state.players_data:
                        full_name = f"{p['last_name'].strip()} {p['first_name'].strip()}"
                        players_list.append(full_name)
                        if show_rating_fields:
                            nat = p["nat_rating"]; fide = p["fide_rating"]
                            nat_val = default_rating if nat == "" else int(nat) if nat.isdigit() else default_rating
                            fide_val = default_rating if fide == "" else int(fide) if fide.isdigit() else default_rating
                            ratings_dict[full_name] = {"nat": nat_val, "fide": fide_val}

                    st.session_state.players = players_list
                    st.session_state.tournament_type = tournament_type
                    st.session_state.scores = {p: 0.0 for p in players_list}
                    st.session_state.ratings = ratings_dict
                    st.session_state.opponents = defaultdict(list)
                    st.session_state.played_pairs.clear()
                    st.session_state.bye_history.clear()
                    st.session_state.tour_data = {}
                    st.session_state.completed = False
                    st.session_state.total_rounds = total_rounds
                    st.session_state.color_history = defaultdict(list)
                    st.session_state.white_count = defaultdict(int)
                    st.session_state.bye_count = defaultdict(int)

                    is_round_robin = (tournament_type in ["Один круг", "Два круга"])
                    if is_round_robin:
                        st.session_state.round_robin_schedule = generate_round_robin_schedule(players_list, total_rounds)

                    for rnd in range(1, total_rounds + 1):
                        st.session_state.tour_data[rnd] = {"pairs": [], "bye": None, "results": [], "completed": False}

                    # Первый тур
                    if is_round_robin:
                        if not st.session_state.round_robin_schedule:
                            st.error("Расписание кругового турнира не сгенерировано.")
                            return
                        round_pairs = st.session_state.round_robin_schedule[0]
                        real_pairs = []; bye = None
                        for p1, p2 in round_pairs:
                            if p1 is None: 
                                bye = p2
                                st.session_state.bye_count[p2] += 1
                            elif p2 is None: 
                                bye = p1
                                st.session_state.bye_count[p1] += 1
                            else: 
                                real_pairs.append((p1, p2))
                        balanced_pairs = assign_colors_round_robin(
                            real_pairs,
                            st.session_state.white_count,
                            st.session_state.bye_count,
                            st.session_state.color_history
                        )
                        st.session_state.tour_data[1]["pairs"] = balanced_pairs
                        st.session_state.tour_data[1]["bye"] = bye
                    else:
                        pairs, bye = initial_pairing_with_colors(players_list[:], st.session_state.color_history, 1, total_rounds)
                        st.session_state.tour_data[1]["pairs"] = pairs
                        st.session_state.tour_data[1]["bye"] = bye
                        if bye: st.session_state.bye_history.add(bye)

                    st.session_state.current_round = 1
                    st.session_state.initialized = True
                    st.rerun()

# =============== Активный турнир ===============
if st.session_state.initialized and not st.session_state.completed:
    current = st.session_state.current_round
    data = st.session_state.tour_data[current]

    st.subheader(f"Тур {current}")

    if data["completed"]:
        st.success("✅ Тур завершён")
        for white, black, res in data["results"]:
            st.write(f"**{white} (Б) — {black} (Ч)**: {res}")
        if data["bye"]:
            st.info(f"BYE: {data['bye']} (+1 очко)")
        if current < st.session_state.total_rounds:
            if st.button(f"Перейти к туру {current + 1}"):
                st.session_state.current_round += 1
                next_rnd = current + 1
                if not st.session_state.tour_data[next_rnd]["pairs"]:
                    is_round_robin = (st.session_state.tournament_type in ["Один круг", "Два круга"])
                    if is_round_robin:
                        if not st.session_state.round_robin_schedule:
                            st.error("Расписание кругового турнира не сгенерировано.")
                            return
                        round_pairs = st.session_state.round_robin_schedule[next_rnd - 1]
                        real_pairs = []; bye = None
                        for p1, p2 in round_pairs:
                            if p1 is None: 
                                bye = p2
                                st.session_state.bye_count[p2] += 1
                            elif p2 is None: 
                                bye = p1
                                st.session_state.bye_count[p1] += 1
                            else: 
                                real_pairs.append((p1, p2))
                        balanced_pairs = assign_colors_round_robin(
                            real_pairs,
                            st.session_state.white_count,
                            st.session_state.bye_count,
                            st.session_state.color_history
                        )
                        st.session_state.tour_data[next_rnd]["pairs"] = balanced_pairs
                        st.session_state.tour_data[next_rnd]["bye"] = bye
                    else:
                        pairs, bye = swiss_pairing_with_colors(
                            st.session_state.players,
                            st.session_state.scores,
                            st.session_state.played_pairs,
                            st.session_state.bye_history,
                            st.session_state.color_history,
                            next_rnd,
                            st.session_state.total_rounds
                        )
                        st.session_state.tour_data[next_rnd]["pairs"] = pairs
                        st.session_state.tour_data[next_rnd]["bye"] = bye
                        if bye:
                            st.session_state.bye_history.add(bye)
                st.rerun()
        else:
            if st.button("Завершить турнир"):
                st.session_state.completed = True
                st.rerun()
    else:
        results = []
        for i, (p1, p2) in enumerate(data["pairs"]):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{p1} (Б) — {p2} (Ч)**")
            with col2:
                res = st.selectbox(f"Результат {i+1}", ["1-0", "0-1", "1/2-1/2"], index=2, key=f"res_{current}_{i}", label_visibility="collapsed")
                results.append((p1, p2, res))

        if data["bye"]:
            st.info(f"BYE: {data['bye']} (+1 очко)")

        if st.button("Завершить тур", type="primary"):
            for white, black, res in results:
                st.session_state.opponents[white].append(black)
                st.session_state.opponents[black].append(white)
                st.session_state.played_pairs.add(frozenset({white, black}))
                if st.session_state.tournament_type == "Швейцарская система":
                    st.session_state.color_history[white].append('Б')
                    st.session_state.color_history[black].append('Ч')
                if res == "1-0": st.session_state.scores[white] += 1.0
                elif res == "0-1": st.session_state.scores[black] += 1.0
                elif res == "1/2-1/2": st.session_state.scores[white] += 0.5; st.session_state.scores[black] += 0.5

            if data["bye"]:
                st.session_state.scores[data["bye"]] += 1.0

            st.session_state.tour_data[current]["results"] = results
            st.session_state.tour_data[current]["completed"] = True

            if current == st.session_state.total_rounds:
                st.session_state.completed = True

            st.rerun()

# =============== Таблица результатов ===============
if st.session_state.initialized:
    st.divider()
    st.subheader("Таблица результатов")

    buchholz = calculate_buchholz(st.session_state.players, st.session_state.scores, st.session_state.opponents)

    sorted_players = sorted(st.session_state.players, key=lambda x: (-st.session_state.scores[x], -buchholz[x], x))

    table_data = []
    place = 1
    prev_key = None
    for name in sorted_players:
        score = st.session_state.scores[name]
        bh = buchholz[name]
        current_key = (score, bh)
        displayed_place = place if prev_key is None or current_key != prev_key else displayed_place
        medal = " 👑" if displayed_place == 1 else " 🥈" if displayed_place == 2 else " 🥉" if displayed_place == 3 else ""
        color_hist = st.session_state.color_history[name]
        white_count = color_hist.count('Б')
        total_games = len(color_hist)
        color_info = f"{white_count}/{total_games}" if total_games > 0 else "0/0"
        table_data.append({"Место": displayed_place, "Имя": name + medal, "Очки": f"{score:.1f}", "Бухгольц": f"{bh:.1f}", "Белых": color_info})
        prev_key = current_key
        place += 1

    st.dataframe(table_data, use_container_width=True, hide_index=True)

if st.session_state.completed:
    st.balloons()
    st.success("🏆 Турнир завершён! Поздравляем победителей!")


