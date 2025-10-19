import streamlit as st
import random
import math
from collections import defaultdict

# =============== Вспомогательные функции ===============

def generate_round_robin_schedule(players):
    """Генерация расписания кругового турнира."""
    players = players[:]
    n = len(players)
    if n % 2 == 1:
        players.append("BYE")
        n += 1

    rounds = []
    for r in range(n - 1):
        pairs = []
        for i in range(n // 2):
            p1 = players[i]
            p2 = players[n - 1 - i]
            if p1 == "BYE":
                pairs.append((None, p2))
            elif p2 == "BYE":
                pairs.append((p1, None))
            else:
                pairs.append((p1, p2))
        rounds.append(pairs)
        players = [players[0]] + [players[-1]] + players[1:-1]
    return rounds

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
if "initialized" not in st.session_state:
    st.session_state.initialized = False
    st.session_state.players = []
    st.session_state.scores = {}
    st.session_state.opponents = defaultdict(list)
    st.session_state.played_pairs = set()
    st.session_state.bye_history = set()
    st.session_state.total_rounds = 0
    st.session_state.current_round = 0
    st.session_state.is_round_robin = False
    st.session_state.round_robin_schedule = []
    st.session_state.tour_data = {}
    st.session_state.completed = False

# =============== Инструкция (простая, без формул) ===============
with st.expander("📌 Инструкция", expanded=not st.session_state.initialized):
    st.markdown("""
    **Как пользоваться программой:**

    1. **Введите имена участников** — через запятую или по одному на строке.  
       Пример: `Анна, Борис, Вера` или просто вставьте список.

    2. **Тип турнира выбирается автоматически:**  
       • **2–8 участников** → круговой турнир (каждый играет с каждым);  
       • **9 и больше** → швейцарская система (участники играют с соперниками с похожим счётом).

    3. **Для швейцарской системы** вы сможете выбрать, сколько туров провести.  
       Программа сама предложит **разумный диапазон**:  
       – не слишком мало (чтобы можно было определить победителя),  
       – и не слишком много (чтобы никто не играл дважды с одним и тем же соперником).

    4. **Во время туров:**  
       – Выберите результат каждой партии: победа одного, победа другого или ничья;  
       – Если участников нечётное число, один отдыхает и получает **BYE** (+1 очко).

    5. **Таблица результатов** обновляется автоматически:  
       – Сортировка: сначала по очкам, затем по дополнительному коэффициенту (Бухгольц);  
       – Первые три места отмечены медалями: 👑 🥈 🥉

    Удачи в турнире! ♟️
    """)

# =============== Ввод участников и выбор числа туров ===============
if not st.session_state.initialized:
    names_input = st.text_area(
        "Введите имена участников (через запятую или по одной):",
        height=100,
        placeholder="Анна, Борис, Вера\nили\nАнна\nБорис\nВера"
    )

    names = []
    raw = names_input.strip()
    if raw:
        names = [n.strip() for n in raw.replace("\n", ",").split(",") if n.strip()]
        names = list(dict.fromkeys(names))

    n_players = len(names)
    is_round_robin = (2 <= n_players <= 8)

    if n_players > 0:
        st.info(f"Участников: {n_players} → {'круговой турнир' if is_round_robin else 'швейцарская система'}")

    total_rounds_input = 6
    if n_players >= 9:
        # Максимум без повторных встреч = число туров в круговом турнире
        if n_players % 2 == 1:
            max_rounds_circle = n_players
        else:
            max_rounds_circle = n_players - 1

        max_allowed = min(11, max_rounds_circle)

        # Минимум: ceil(log2(N)), но не менее 3
        min_theoretical = math.ceil(math.log2(n_players))
        min_allowed = max(3, min_theoretical)

        if min_allowed > max_allowed:
            min_allowed = max_allowed

        default_rounds = min(min_allowed + 2, max_allowed)

        total_rounds_input = st.slider(
            "Выберите количество туров:",
            min_value=min_allowed,
            max_value=max_allowed,
            value=default_rounds,
            help=f"Для {n_players} участников максимально возможное число туров без повторных встреч — {max_rounds_circle}."
        )
    elif is_round_robin:
        auto_rounds = n_players - 1 if n_players % 2 == 0 else n_players
        st.info(f"Круговой турнир: автоматически {auto_rounds} туров.")

    if st.button("Начать турнир", type="primary"):
        if not raw:
            st.error("Введите хотя бы одно имя!")
        elif n_players < 2:
            st.error("Нужно минимум 2 участника!")
        else:
            st.session_state.players = names
            st.session_state.is_round_robin = is_round_robin
            st.session_state.scores = {p: 0.0 for p in names}
            st.session_state.opponents = defaultdict(list)
            st.session_state.played_pairs.clear()
            st.session_state.bye_history.clear()
            st.session_state.tour_data = {}
            st.session_state.completed = False

            if is_round_robin:
                st.session_state.total_rounds = n_players - 1 if n_players % 2 == 0 else n_players
            else:
                st.session_state.total_rounds = total_rounds_input

            if is_round_robin:
                st.session_state.round_robin_schedule = generate_round_robin_schedule(names)

            for rnd in range(1, st.session_state.total_rounds + 1):
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
                pairs, bye = initial_pairing(names[:])
                st.session_state.tour_data[1]["pairs"] = pairs
                st.session_state.tour_data[1]["bye"] = bye
                if bye:
                    st.session_state.bye_history.add(bye)

            st.session_state.current_round = 1
            st.session_state.initialized = True
            st.rerun()

# =============== Основной интерфейс после старта ===============
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
                    if st.session_state.is_round_robin:
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
