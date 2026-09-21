import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import random
import json

# ==================== 1. 初始化 Firebase ====================
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        if "firebase" in st.secrets:
            key_dict = dict(st.secrets["firebase"])
            cred = credentials.Certificate(key_dict)
        else:
            cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

# ==================== 2. 演算法函式 ====================
def derangement_shuffle(names):
    shuffled = names.copy()
    random.shuffle(shuffled)
    pairs = {}
    for i in range(len(shuffled)):
        giver = shuffled[i]
        receiver = shuffled[(i + 1) % len(shuffled)]
        pairs[giver] = receiver
    return pairs

# ==================== 3. 頁面設定與可愛 App CSS ====================
st.set_page_config(page_title="派對抽獎小助手", layout="centered", page_icon="🎁")

st.markdown("""
<style>
    /* 整體背景 */
    .stApp {
        background: linear-gradient(180deg, #fff7f7 0%, #f7f9fa 100%);
    }
    header, footer {visibility: hidden;}

    /* 確保所有元素置中對齊 */
    .stMainBlockContainer, [data-testid="stVerticalBlock"] {
        align-items: center !important;
        text-align: center !important;
    }

    /* 標題與文字居中 */
    .app-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #ff5a5f;
        margin-top: 1.5rem;
        margin-bottom: 0.2rem;
        text-align: center;
    }
    .app-subtitle {
        color: #718096;
        font-size: 1rem;
        margin-bottom: 2rem;
        text-align: center;
    }

    /* 首頁圓形按鈕樣式 */
    .circle-btn-container div.stButton > button {
        width: 140px !important;
        height: 140px !important;
        border-radius: 50% !important;
        font-size: 1.1rem !important;
        font-weight: 800 !important;
        border: 4px solid #ffffff !important;
        box-shadow: 0 10px 25px rgba(255, 90, 95, 0.15) !important;
        background: #ffffff !important;
        color: #2d3748 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin: 0 auto !important;
        transition: all 0.25s ease !important;
        white-space: pre-wrap !important;
        line-height: 1.4 !important;
    }
    .circle-btn-container div.stButton > button:hover {
        transform: translateY(-5px) scale(1.05) !important;
        box-shadow: 0 14px 28px rgba(255, 90, 95, 0.25) !important;
        border-color: #ff5a5f !important;
        color: #ff5a5f !important;
    }

    /* 內頁通用圓角長按鈕 */
    div.stButton > button {
        border-radius: 16px !important;
        font-weight: 700 !important;
        transition: all 0.2s ease !important;
    }
</style>
""", unsafe_allow_html=True)

if "app_page" not in st.session_state:
    st.session_state["app_page"] = "home"

# =========================================================
# 🏠 第一頁：首頁（對齊標題、可愛雙圓形按鈕）
# =========================================================
if st.session_state["app_page"] == "home":
    st.markdown('<div class="app-title">🎁 派對抽獎小助手</div>', unsafe_allow_html=True)
    st.markdown('<div class="app-subtitle">請選擇您要使用的功能：</div>', unsafe_allow_html=True)

    # 用兩欄左右對稱，放置兩個超可愛的大圓形按鈕
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="circle-btn-container">', unsafe_allow_html=True)
        if st.button("🎄\n交換禮物\n專用", key="btn_to_gift"):
            st.session_state["app_page"] = "gift_menu"
            st.session_state["gift_action"] = "menu"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="circle-btn-container">', unsafe_allow_html=True)
        if st.button("🎉\n部門抽獎\n專用", key="btn_to_lotto"):
            st.session_state["app_page"] = "lotto_menu"
            st.session_state["lotto_action"] = "menu"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 🎄 第二層：交換禮物專區
# =========================================================
elif st.session_state["app_page"] == "gift_menu":
    st.markdown('<div class="app-title">🎄 交換禮物專用</div>', unsafe_allow_html=True)

    if "current_gift_room" in st.session_state and st.session_state["current_gift_room"]:
        room_id = st.session_state["current_gift_room"]
        room_ref = db.collection("rooms").document(room_id)
        room_doc = room_ref.get()

        if not room_doc.exists:
            st.error("此房間已不存在！")
            if st.button("返回專區選單"):
                del st.session_state["current_gift_room"]
                st.rerun()
        else:
            room = room_doc.to_dict()
            host_name = room.get("host_name", "房主")
            st.success(f"📍 **{room['room_name']}** ｜ 房號：`{room['room_id']}` ｜ 房主：`{host_name}`")

            if room["status"] == "waiting":
                st.write(f"👥 **已加入名單（共 {len(room['members'])} 人）：**")
                st.info("、".join(room["members"]))

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 刷新名單", key="ref_g"):
                        st.rerun()
                with col2:
                    if st.button("🚪 離開房間", key="exit_g"):
                        del st.session_state["current_gift_room"]
                        st.rerun()

                st.markdown("---")
                st.markdown("#### 👤 成員簽到加入")
                join_name = st.text_input("輸入你的名字：", key="g_join_name").strip()
                join_pass = st.text_input("設定 4 位數個人密碼：", type="password", max_chars=4, key="g_join_pass").strip()

                if st.button("確認簽到加入", type="primary", key="btn_g_confirm"):
                    if not join_name or not join_pass:
                        st.error("名字與密碼不能為空！")
                    elif join_name in room["members"]:
                        st.warning("這個名字已經在名單中囉！")
                    else:
                        room["members"].append(join_name)
                        room["passcodes"][join_name] = join_pass
                        room_ref.update({"members": room["members"], "passcodes": room["passcodes"]})
                        st.success("簽到成功！")
                        st.rerun()

                st.markdown("---")
                with st.expander(f"👑 房主專區（僅限 {host_name} 操作）"):
                    verify_host_pass = st.text_input("請輸入房主密碼：", type="password", key="v_h_pass")
                    if st.button("全員到齊，開始配對開獎！", type="primary", key="btn_start_derange"):
                        if verify_host_pass != room["passcodes"].get(host_name):
                            st.error("❌ 房主密碼錯誤！只有房主能開獎！")
                        elif len(room["members"]) < 2:
                            st.error("至少需要 2 人才能配對！")
                        else:
                            final_pairs = derangement_shuffle(room["members"])
                            room_ref.update({"status": "finished", "pairs": final_pairs})
                            st.rerun()

            elif room["status"] == "finished":
                st.balloons()
                st.success("🎉 配對已完成！紀錄已永久保存於雲端。")
                if st.button("🚪 離開房間", key="exit_g_fin"):
                    del st.session_state["current_gift_room"]
                    st.rerun()

                st.markdown("---")
                st.markdown("#### 🎁 查看我抽到誰（防偷看）")
                my_name = st.selectbox("選擇你的名字：", ["-- 請選擇 --"] + sorted(room["members"]), key="sel_g_my_name")
                my_pass = st.text_input("輸入防窺密碼：", type="password", key="inp_g_my_pass")

                if st.button("揭曉送禮對象 🎯", type="primary", key="btn_reveal_gift"):
                    correct_pass = room["passcodes"].get(my_name)
                    if my_name == "-- 請選擇 --":
                        st.warning("請先選擇你的名字！")
                    elif my_pass != correct_pass:
                        st.error("密碼錯誤，請重新輸入！")
                    else:
                        target = room["pairs"].get(my_name)
                        st.markdown(f"### ✨ **{my_name}**，你抽到的是：👉 **{target}** 👈")

    else:
        st.markdown('<div class="app-subtitle">請選擇操作：</div>', unsafe_allow_html=True)
        action = st.session_state.get("gift_action", "menu")

        if action == "menu":
            if st.button("1. 👑 建立房間", key="btn_g_c"):
                st.session_state["gift_action"] = "create"
                st.rerun()
            if st.button("2. 🔑 手動輸入房號進入", key="btn_g_j"):
                st.session_state["gift_action"] = "join"
                st.rerun()
            if st.button("3. 📜 我的歷史房間", key="btn_g_h"):
                st.session_state["gift_action"] = "history"
                st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("⬅️ 返回首頁", key="btn_g_to_home"):
                st.session_state["app_page"] = "home"
                st.rerun()

        elif action == "create":
            st.subheader("👑 建立交換禮物房間")
            room_name = st.text_input("房間名稱（如：2026 聖誕交換禮物）", key="inp_c_rname")
            host_name = st.text_input("房主姓名（房主亦一同參與）", key="inp_c_hname")
            host_pass = st.text_input("設定房主專用密碼（4位數）", type="password", max_chars=4, key="inp_c_hpass")

            if st.button("確認建立並直接進入 🚀", type="primary", key="btn_act_c_g"):
                if not room_name.strip() or not host_name.strip() or not host_pass.strip():
                    st.error("請完整填寫房名、房主姓名與密碼！")
                else:
                    new_room_id = str(random.randint(100000, 999999))
                    db.collection("rooms").document(new_room_id).set({
                        "room_id": new_room_id,
                        "room_name": room_name.strip(),
                        "type": "gift",
                        "status": "waiting",
                        "host_name": host_name.strip(),
                        "members": [host_name.strip()],
                        "passcodes": {host_name.strip(): host_pass.strip()},
                        "pairs": {}
                    })
                    st.session_state["current_gift_room"] = new_room_id
                    st.session_state["gift_action"] = "menu"
                    st.rerun()
            if st.button("⬅️ 返回", key="b_back_gc"):
                st.session_state["gift_action"] = "menu"
                st.rerun()

        elif action == "join":
            st.subheader("🔑 手動輸入房號進入")
            input_rid = st.text_input("請輸入 6 位數房號：", key="inp_j_grid").strip()
            if st.button("進入房間", type="primary", key="btn_act_j_g"):
                if not input_rid:
                    st.error("請輸入房號！")
                else:
                    doc = db.collection("rooms").document(input_rid).get()
                    if not doc.exists:
                        st.error("找不到此房號！")
                    else:
                        st.session_state["current_gift_room"] = input_rid
                        st.session_state["gift_action"] = "menu"
                        st.rerun()
            if st.button("⬅️ 返回", key="b_back_gj"):
                st.session_state["gift_action"] = "menu"
                st.rerun()

        elif action == "history":
            st.subheader("📜 我的歷史房間卡片")
            st.caption("輸入姓名，雲端自動找出所有你參與過的房間卡片：")
            search_user = st.text_input("輸入你的名字：", key="inp_h_guser").strip()

            if search_user:
                history_query = db.collection("rooms").where("members", "array_contains", search_user).stream()
                found_rooms = [doc.to_dict() for doc in history_query]

                if not found_rooms:
                    st.info(f"雲端找不到關於「{search_user}」的交換禮物紀錄。")
                else:
                    st.write(f"🎉 找到 **{len(found_rooms)}** 個歷史房間：")
                    for r in found_rooms:
                        status_tag = "✅ 已開獎" if r.get("status") == "finished" else "⏳ 進行中"
                        with st.container(border=True):
                            c1, c2 = st.columns([3, 1])
                            with c1:
                                st.markdown(f"**🎁 {r.get('room_name', '未命名房間')}**")
                                st.caption(f"房號：`{r['room_id']}` ｜ 房主：{r.get('host_name')} ｜ {status_tag}")
                            with c2:
                                if st.button("進入卡片 👉", key=f"card_{r['room_id']}"):
                                    st.session_state["current_gift_room"] = r["room_id"]
                                    st.session_state["gift_action"] = "menu"
                                    st.rerun()
            if st.button("⬅️ 返回", key="b_back_gh"):
                st.session_state["gift_action"] = "menu"
                st.rerun()

# =========================================================
# 🎉 第二層：部門抽獎專區
# =========================================================
elif st.session_state["app_page"] == "lotto_menu":
    st.markdown('<div class="app-title">🎉 部門抽獎專用</div>', unsafe_allow_html=True)

    if "current_lotto_room" in st.session_state and st.session_state["current_lotto_room"]:
        l_room_id = st.session_state["current_lotto_room"]
        l_doc_ref = db.collection("lottery_rooms").document(l_room_id)
        l_doc = l_doc_ref.get()

        if not l_doc.exists:
            st.error("抽獎房不存在！")
            if st.button("返回專區選單"):
                del st.session_state["current_lotto_room"]
                st.rerun()
        else:
            l_room = l_doc.to_dict()
            l_host = l_room.get("host_name", "房主")
            st.success(f"📍 **{l_room['room_name']}** ｜ 房號：`{l_room['room_id']}` ｜ 房主：`{l_host}`")

            if l_room["status"] == "waiting":
                st.write(f"👥 **現場抽獎池（共 {len(l_room['members'])} 人）：**")
                st.info("、".join(l_room["members"]))

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 刷新名單", key="ref_l"):
                        st.rerun()
                with col2:
                    if st.button("🚪 離開房間", key="exit_l"):
                        del st.session_state["current_lotto_room"]
                        st.rerun()

                st.markdown("---")
                l_join_name = st.text_input("輸入名字簽到：", key="l_join_name").strip()
                if st.button("簽到加入抽獎", type="primary", key="btn_l_confirm"):
                    if not l_join_name:
                        st.error("名字不能為空！")
                    elif l_join_name in l_room["members"]:
                        st.warning("你已在名單中囉！")
                    else:
                        l_room["members"].append(l_join_name)
                        l_doc_ref.update({"members": l_room["members"]})
                        st.success("簽到成功！")
                        st.rerun()

                st.markdown("---")
                with st.expander(f"👑 房主開獎專區（僅限 {l_host} 操作）"):
                    v_l_host_pass = st.text_input("請輸入房主密碼：", type="password", key="vl_h_pass")
                    draw_num = st.number_input("抽出幾個人？", min_value=1, max_value=max(1, len(l_room["members"])), value=1, step=1, key="lotto_draw_num")
                    if st.button("確認開獎 🎊", type="primary", key="btn_act_draw_lotto"):
                        if v_l_host_pass != l_room.get("host_pass"):
                            st.error("❌ 房主密碼錯誤！只有房主能開獎！")
                        elif len(l_room["members"]) == 0:
                            st.error("名單內沒有人！")
                        else:
                            winners = random.sample(l_room["members"], int(draw_num))
                            l_doc_ref.update({"status": "finished", "winners": winners, "draw_count": int(draw_num)})
                            st.rerun()

            elif l_room["status"] == "finished":
                st.balloons()
                st.success(f"🎉 開獎完畢！共抽出 {len(l_room['winners'])} 位得獎者：")
                for idx, w in enumerate(l_room["winners"], start=1):
                    st.markdown(f"### 🏆 第 {idx} 名：{w}")

                with st.expander("檢視所有參與者名單"):
                    st.write("、".join(l_room["members"]))

                if st.button("🚪 離開房間", key="exit_l_fin"):
                    del st.session_state["current_lotto_room"]
                    st.rerun()

    else:
        st.markdown('<div class="app-subtitle">請選擇操作：</div>', unsafe_allow_html=True)
        l_action = st.session_state.get("lotto_action", "menu")

        if l_action == "menu":
            if st.button("1. 👑 建立房間", key="btn_l_c"):
                st.session_state["lotto_action"] = "create"
                st.rerun()
            if st.button("2. 🔑 手動輸入房號進入", key="btn_l_j"):
                st.session_state["lotto_action"] = "join"
                st.rerun()
            if st.button("3. 📜 我的歷史房間", key="btn_l_h"):
                st.session_state["lotto_action"] = "history"
                st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("⬅️ 返回首頁", key="btn_l_to_home"):
                st.session_state["app_page"] = "home"
                st.rerun()

        elif l_action == "create":
            st.subheader("👑 建立現場抽獎房")
            new_l_name = st.text_input("抽獎活動名稱（如：會計部尾牙）", key="inp_nl_name")
            new_l_host = st.text_input("房主姓名", key="inp_nl_host")
            new_l_pass = st.text_input("設定房主專用密碼（4位數）", type="password", max_chars=4, key="inp_nl_pass")

            if st.button("確認建立並進入 🚀", type="primary", key="btn_act_c_l"):
                if not new_l_name.strip() or not new_l_host.strip() or not new_l_pass.strip():
                    st.error("請完整填寫活動名稱、房主姓名與密碼！")
                else:
                    new_l_id = str(random.randint(100000, 999999))
                    db.collection("lottery_rooms").document(new_l_id).set({
                        "room_id": new_l_id, "room_name": new_l_name.strip(), "host_name": new_l_host.strip(),
                        "host_pass": new_l_pass.strip(), "status": "waiting", "members": [new_l_host.strip()],
                        "winners": [], "draw_count": 0
                    })
                    st.session_state["current_lotto_room"] = new_l_id
                    st.session_state["lotto_action"] = "menu"
                    st.rerun()
            if st.button("⬅️ 返回", key="b_back_lc"):
                st.session_state["lotto_action"] = "menu"
                st.rerun()

        elif l_action == "join":
            st.subheader("🔑 手動輸入房號進入")
            input_l_id = st.text_input("請輸入 6 位數抽獎房號：", key="inp_jl_id").strip()
            if st.button("進入抽獎房", type="primary", key="btn_act_j_l"):
                if not input_l_id:
                    st.error("請輸入房號！")
                else:
                    doc = db.collection("lottery_rooms").document(input_l_id).get()
                    if not doc.exists:
                        st.error("找不到此抽獎房號！")
                    else:
                        st.session_state["current_lotto_room"] = input_l_id
                        st.session_state["lotto_action"] = "menu"
                        st.rerun()
            if st.button("⬅️ 返回", key="b_back_lj"):
                st.session_state["lotto_action"] = "menu"
                st.rerun()

        elif l_action == "history":
            st.subheader("📜 歷史抽獎活動卡片")
            search_lotto = db.collection("lottery_rooms").stream()
            all_lottos = [doc.to_dict() for doc in search_lotto]
            if all_lottos:
                for al in all_lottos:
                    l_stat = "✅ 已開獎" if al.get("status") == "finished" else "⏳ 進行中"
                    with st.container(border=True):
                        st.markdown(f"**🎉 {al.get('room_name')}**（房號：`{al['room_id']}`）- {l_stat}")
                        if st.button("查看此結果 👉", key=f"btn_l_{al['room_id']}"):
                            st.session_state["current_lotto_room"] = al["room_id"]
                            st.session_state["lotto_action"] = "menu"
                            st.rerun()
            else:
                st.info("尚無歷史抽獎紀錄。")
            if st.button("⬅️ 返回", key="b_back_lh"):
                st.session_state["lotto_action"] = "menu"
                st.rerun()
