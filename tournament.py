import streamlit as st
import random
import math
from collections import defaultdict

# =============== Вспомогательные функции ===============

def generate_round_robin_schedule(players, rounds_needed):
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
            second_circle.append(pairs)
        full_schedule.extend(second_circle)

    return full_schedule[:rounds_needed]

def initial_pairing(players):
    random.shuffle(players)
    pairs = [(players[i], players[i+1]) for i in range(0, len(players) - 1, 2)]
    bye = players[-1] if len(players) % 2 == 1 else None
    return pairs, bye

def swiss_pairing(players, scores, played_pairs, bye_history):
    n = len(players)
    is_odd = (n % 2 == 1)
    sorted_players = sorted(players, key=lambda x: (-scores[x], random.random()))
    paired = set()
    pairs = []

    for i, p1 in enumerate(sorted_players):
        if p1 in paired:
            continue
        opponent = None
        for p2 in sorted_players[i+1:]:
            if p2 in paired:
                continue
            if frozenset({p1, p2}) in played_pairs:
                continue
            if abs(scores[p1] - scores[p2]) <= 0.5:
                opponent = p2
                break
        if opponent:
            pairs.append((p1, opponent))
            paired.add(p1)
            paired.add(opponent)
            played_pairs.add(frozenset({p1, p2}))

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
                    pairs.append((a, b))
                    played_pairs.add(frozenset({a, b}))
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

# Инициализация состояния
if "step" not in st.session_state:
    st.session_state.step = "players"  # "players", "rounds", "active"
if "players_data" not in st.session_state:
    st.session_state.players_data = []
if "use_ratings" not in st.session_state:
    st.session_state.use_ratings = False
if "default_rating" not in st.session_state:
    st.session_state.default_rating = 1000

# Состояния турнира
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
    st.session_state.ratings = {}  # для будущего использования

# =============== Вкладки ===============
if not st.session_state.initialized:
    tabs = st.tabs(["Игроки и рейтинги", "Туры"])
    
    # =============== Вкладка 1: Игроки и рейтинги ===============
    with tabs[0]:
        st.subheader("Игроки")
        
        # Кнопки управления
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ Добавить игрока"):
                st.session_state.players_data.append({
                    "last_name": "", "first_name": "",
                    "nat_rating": "", "fide_rating": "",
                    "fshr_id": "", "fide_id": ""
                })
        with col2:
            if st.button("🗑️ Удалить последнего") and st.session_state.players_
                st.session_state.players_data.pop()

        # Чекбокс для рейтинговой информации
        use_ratings = st.checkbox("Добавить рейтинговую информацию", value=st.session_state.use_ratings)
        st.session_state.use_ratings = use_ratings

        if use_ratings:
            st.session_state.default_rating = st.number_input(
                "Рейтинг по умолчанию",
                value=st.session_state.default_rating,
                min_value=0,
                step=1
            )

        # Поля ввода для каждого игрока
        for i, player in enumerate(st.session_state.players_data):
            st.markdown(f"**Игрок {i+1}**")
            cols = st.columns(2)
            with cols[0]:
                last_name = st.text_input(
                    "Фамилия", 
                    value=player["last_name"], 
                    key=f"last_{i}"
                )
            with cols[1]:
                first_name = st.text_input(
                    "Имя", 
                    value=player["first_name"], 
                    key=f"first_{i}"
                )
            
            if use_ratings:
                cols2 = st.columns(4)
                with cols2[0]:
                    nat_rating = st.text_input("Национальный рейтинг", value=str(player["nat_rating"]) if player["nat_rating"] != "" else "", key=f"nat_{i}")
                with cols2[1]:
                    fide_rating = st.text_input("Рейтинг FIDE", value=str(player["fide_rating"]) if player["fide_rating"] != "" else "", key=f"fide_{i}")
                with cols2[2]:
                    fshr_id = st.text_input("ID ФШР", value=player["fshr_id"], key=f"fshr_{i}")
                with cols2[3]:
                    fide_id = st.text_input("ID FIDE", value=player["fide_id"], key=f"id_{i}")
                
                st.session_state.players_data[i] = {
                    "last_name": last_name,
                    "first_name": first_name,
                    "nat_rating": nat_rating,
                    "fide_rating": fide_rating,
                    "fshr_id": fshr_id,
                    "fide_id": fide_id
                }
            else:
                st.session_state.players_data[i] = {
                    "last_name": last_name,
                    "first_name": first_name,
                    "nat_rating": "", "fide_rating": "",
                    "fshr_id": "", "fide_id": ""
                }
            st.divider()

    # =============== Вкладка 2: Туры ===============
    with tabs[1]:
        # Формируем список имён для подсчёта N
        valid_players = [
            p for p in st.session_state.players_data 
            if p["last_name"].strip() and p["first_name"].strip()
        ]
        n_players = len(valid_players)

        if n_players == 0:
            st.warning("Добавьте хотя бы одного игрока на вкладке «Игроки и рейтинги».")
        else:
            st.info(f"Участников: {n_players}")
            total_rounds = None
            tournament_type = None

            if n_players < 7:
                tournament_type = st.radio(
                    "Выберите тип турнира:",
                    options=["Один круг", "Два круга"],
                    index=0,
                    help="При менее чем 7 участниках швейцарская система не рекомендуется."
                )
                if tournament_type == "Один круг":
                    total_rounds = n_players if n_players % 2 == 1 else n_players - 1
                else:
                    base = n_players if n_players % 2 == 1 else n_players - 1
                    total_rounds = 2 * base
            else:
                tournament_type = st.radio(
                    "Выберите тип турнира:",
                    options=["Один круг", "Два круга", "Швейцарская система"],
                    index=2
                )
                if tournament_type == "Один круг":
                    total_rounds = n_players if n_players % 2 == 1 else n_players - 1
                elif tournament_type == "Два круга":
                    base = n_players if n_players % 2 == 1 else n_players - 1
                    total_rounds = 2 * base
                else:
                    recommended = math.ceil(math.log2(n_players)) + 2
                    max_circle = n_players if n_players % 2 == 1 else n_players - 1
                    max_swiss = min(max_circle, recommended + 2)
                    min_swiss = recommended
                    if min_swiss > max_swiss:
                        min_swiss = max_swiss
                    total_rounds = st.slider(
                        "Количество туров:",
                        min_value=min_swiss,
                        max_value=max_swiss,
                        value=recommended,
                        help=f"Рекомендуется {recommended} туров. Максимум без повторных встреч: {max_circle}."
                    )

            if st.button("Начать турнир", type="primary"):
                # Валидация
                errors = []
                for i, p in enumerate(st.session_state.players_data):
                    if not p["last_name"].strip():
                        errors.append(f"У игрока {i+1} не указана фамилия.")
                    if not p["first_name"].strip():
                        errors.append(f"У игрока {i+1} не указано имя.")
                if errors:
                    for err in errors:
                        st.error(err)
                elif tournament_type is None:
                    st.error("Выберите тип турнира.")
                else:
                    # Обработка рейтингов
                    players_list = []
                    ratings_dict = {}
                    default_rating = st.session_state.default_rating
                    use_ratings = st.session_state.use_ratings

                    for p in st.session_state.players_data:
                        full_name = f"{p['last_name'].strip()} {p['first_name'].strip()}"
                        players_list.append(full_name)

                        if use_ratings:
                            nat = p["nat_rating"]
                            fide = p["fide_rating"]
                            nat_val = default_rating if nat == "" else int(nat) if nat.isdigit() else default_rating
                            fide_val = default_rating if fide == "" else int(fide) if fide.isdigit() else default_rating
                            ratings_dict[full_name] = {"nat": nat_val, "fide": fide_val}

                    # Инициализация турнира
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

                    is_round_robin = (tournament_type in ["Один круг", "Два круга"])
                    if is_round_robin:
                        st.session_state.round_robin_schedule = generate_round_robin_schedule(players_list, total_rounds)

                    for rnd in range(1, total_rounds + 1):
                        st.session_state.tour_data[rnd] = {
                            "pairs": [],
                            "bye": None,
                            "results": [],
                            "completed": False
                        }

                    # Первый тур
                    if is_round_robin:
                        round_pairs = st.session_state.round_robin_schedule[0]
                        real_pairs = []
                        bye = None
                        for p1, p2 in round_pairs:
                            if p1 is None:
                                bye = p2
                            elif p2 is None:
                                bye = p1
                            else:
                                real_pairs.append((p1, p2))
                        st.session_state.tour_data[1]["pairs"] = real_pairs
                        st.session_state.tour_data[1]["bye"] = bye
                    else:
                        pairs, bye = initial_pairing(players_list[:])
                        st.session_state.tour_data[1]["pairs"] = pairs
                        st.session_state.tour_data[1]["bye"] = bye
                        if bye:
                            st.session_state.bye_history.add(bye)

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
        for p1, p2, res in data["results"]:
            st.write(f"**{p1} — {p2}**: {res}")
        if data["bye"]:
            st.info(f"BYE: {data['bye']} (+1 очко)")
        if current < st.session_state.total_rounds:
            if st.button(f"Перейти к туру {current + 1}"):
                st.session_state.current_round += 1
                next_rnd = current + 1
                if not st.session_state.tour_data[next_rnd]["pairs"]:
                    is_round_robin = (st.session_state.tournament_type in ["Один круг", "Два круга"])
                    if is_round_robin:
                        round_pairs = st.session_state.round_robin_schedule[next_rnd - 1]
                        real_pairs = []
                        bye = None
                        for p1, p2 in round_pairs:
                            if p1 is None:
                                bye = p2
                            elif p2 is None:
                                bye = p1
                            else:
                                real_pairs.append((p1, p2))
                        st.session_state.tour_data[next_rnd]["pairs"] = real_pairs
                        st.session_state.tour_data[next_rnd]["bye"] = bye
                    else:
                        pairs, bye = swiss_pairing(
                            st.session_state.players,
                            st.session_state.scores,
                            st.session_state.played_pairs,
                            st.session_state.bye_history
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
                st.write(f"**{p1} — {p2}**")
            with col2:
                res = st.selectbox(
                    f"Результат {i+1}",
                    options=["1-0", "0-1", "1/2-1/2"],
                    index=2,
                    key=f"res_{current}_{i}",
                    label_visibility="collapsed"
                )
                results.append((p1, p2, res))

        if data["bye"]:
            st.info(f"BYE: {data['bye']} (+1 очко)")

        if st.button("Завершить тур", type="primary"):
            for p1, p2, res in results:
                st.session_state.opponents[p1].append(p2)
                st.session_state.opponents[p2].append(p1)
                st.session_state.played_pairs.add(frozenset({p1, p2}))
                if res == "1-0":
                    st.session_state.scores[p1] += 1.0
                elif res == "0-1":
                    st.session_state.scores[p2] += 1.0
                elif res == "1/2-1/2":
                    st.session_state.scores[p1] += 0.5
                    st.session_state.scores[p2] += 0.5

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

    buchholz = calculate_buchholz(
        st.session_state.players,
        st.session_state.scores,
        st.session_state.opponents
    )

    sorted_players = sorted(
        st.session_state.players,
        key=lambda x: (-st.session_state.scores[x], -buchholz[x], x)
    )

    table_data = []
    place = 1
    prev_key = None
    for name in sorted_players:
        score = st.session_state.scores[name]
        bh = buchholz[name]
        current_key = (score, bh)
        displayed_place = place if prev_key is None or current_key != prev_key else displayed_place
        medal = " 👑" if displayed_place == 1 else " 🥈" if displayed_place == 2 else " 🥉" if displayed_place == 3 else ""
        table_data.append({
            "Место": displayed_place,
            "Имя": name + medal,
            "Очки": f"{score:.1f}",
            "Бухгольц": f"{bh:.1f}"
        })
        prev_key = current_key
        place += 1

    st.dataframe(table_data, use_container_width=True, hide_index=True)

# =============== Завершение ===============
if st.session_state.completed:
    st.balloons()
    st.success("🏆 Турнир завершён! Поздравляем победителей!")
