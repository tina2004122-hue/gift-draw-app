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
    """環狀閉環配對：保證無人抽到自己、無重複、成完整閉環"""
    shuffled = names.copy()
    random.shuffle(shuffled)
    pairs = {}
    for i in range(len(shuffled)):
        giver = shuffled[i]
        receiver = shuffled[(i + 1) % len(shuffled)]
        pairs[giver] = receiver
    return pairs

# ==================== 3. 介面主邏輯 ====================
st.set_page_config(page_title="活動抽獎與交換禮物", layout="centered", page_icon="🎁")

tab1, tab2 = st.tabs(["🎄 交換禮物專用", "🎉 部門抽獎專用"])

# -------------------- TAB 1: 交換禮物 --------------------
with tab1:
    st.header("🎁 交換禮物房間")

    # 判斷是否已在特定房間內
    if "current_gift_room" in st.session_state and st.session_state["current_gift_room"]:
        room_id = st.session_state["current_gift_room"]
        room_ref = db.collection("rooms").document(room_id)
        room_doc = room_ref.get()

        if not room_doc.exists:
            st.error("此房間已不存在！")
            if st.button("返回大廳", key="back_gift_hall"):
                del st.session_state["current_gift_room"]
                st.rerun()
        else:
            room = room_doc.to_dict()
            host_name = room.get("host_name", "房主")
            st.info(f"📍 房間名稱：**{room['room_name']}** ｜ 房號：**{room['room_id']}** ｜ 房主：**{host_name}**")

            # 狀態 1：等待報名中
            if room["status"] == "waiting":
                st.subheader("👥 成員簽到清單")
                st.write(f"目前已加入（共 {len(room['members'])} 人）：")
                st.success("、".join(room["members"]))

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 刷新名單", key="ref_gift"):
                        st.rerun()
                with col2:
                    if st.button("🚪 退出房間", key="exit_gift"):
                        del st.session_state["current_gift_room"]
                        st.rerun()

                st.markdown("---")
                st.markdown("#### 👤 成員簽到加入")
                join_name = st.text_input("輸入你的名字：", key="join_name_input").strip()
                join_pass = st.text_input("設定 4 位數個人防窺密碼：", type="password", max_chars=4, key="join_pass_input").strip()

                if st.button("確認簽到加入", key="btn_confirm_join_gift"):
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
                    st.caption("防誤觸保護：輸入房主密碼方可啟動配對")
                    verify_host_pass = st.text_input("請輸入房主密碼：", type="password", key="v_h_pass")
                    if st.button("全員到齊，開始配對開獎！", type="primary", key="btn_gift_start_draw"):
                        if verify_host_pass != room["passcodes"].get(host_name):
                            st.error("❌ 房主密碼錯誤！只有房主可以按開獎！")
                        elif len(room["members"]) < 2:
                            st.error("至少需要 2 人才能配對！")
                        else:
                            final_pairs = derangement_shuffle(room["members"])
                            room_ref.update({"status": "finished", "pairs": final_pairs})
                            st.rerun()

            # 狀態 2：配對已完成（查看/隔年回溯結果）
            elif room["status"] == "finished":
                st.success("🎉 配對已完成！本活動紀錄已永久保存於雲端。")
                if st.button("🚪 退出房間（回首頁）", key="exit_gift_fin"):
                    del st.session_state["current_gift_room"]
                    st.rerun()

                st.markdown("---")
                st.markdown("#### 🎁 查看我抽到誰（防偷看保護）")
                my_name = st.selectbox("選擇你的名字：", ["-- 請選擇 --"] + sorted(room["members"]), key="sb_gift_name")
                my_pass = st.text_input("輸入當初設定的防窺密碼：", type="password", key="view_pass_input")

                if st.button("揭曉我的送禮對象 🎯", key="btn_reveal_gift"):
                    correct_pass = room["passcodes"].get(my_name)
                    if my_name == "-- 請選擇 --":
                        st.warning("請先選擇你的名字！")
                    elif my_pass != correct_pass:
                        st.error("密碼錯誤，請重新輸入！")
                    else:
                        target = room["pairs"].get(my_name)
                        st.balloons()
                        st.markdown(f"### ✨ **{my_name}**，你抽到的是：👉 **{target}** 👈")
                        st.caption("記好後可選回空白，避免旁人看見。")

    # 未進房狀態：首頁
    else:
        # ===== 雲端歷史卡片專區 =====
        with st.expander("📜 我的歷史房間（卡片回溯專區）", expanded=True):
            st.caption("輸入你的名字，雲端直接找出你參加過的所有歷史房間卡片：")
            search_user = st.text_input("輸入姓名查歷史卡片：", key="search_user_history").strip()
            
            if search_user:
                history_query = db.collection("rooms").where("members", "array_contains", search_user).stream()
                found_rooms = [doc.to_dict() for doc in history_query]

                if not found_rooms:
                    st.info(f"雲端找不到關於「{search_user}」的交換禮物紀錄。")
                else:
                    st.write(f"🎉 找到 **{len(found_rooms)}** 個你參與過的房間卡片：")
                    for r in found_rooms:
                        status_tag = "✅ 已開獎" if r.get("status") == "finished" else "⏳ 進行中"
                        with st.container(border=True):
                            c_col1, c_col2 = st.columns([3, 1])
                            with c_col1:
                                st.markdown(f"### 🎁 {r.get('room_name', '未命名房間')}")
                                st.caption(f"房號：`{r['room_id']}` ｜ 房主：{r.get('host_name')} ｜ 狀態：{status_tag}")
                            with c_col2:
                                if st.button("進入卡片 👉", key=f"card_{r['room_id']}"):
                                    st.session_state["current_gift_room"] = r["room_id"]
                                    st.rerun()

        st.markdown("---")
        action = st.radio("選擇操作", ["建立新房間", "手動輸入房號進入"], horizontal=True, key="gift_action_radio")

        if action == "建立新房間":
            st.subheader("建立交換禮物房間")
            room_name = st.text_input("房間名稱（如：2026 大學聖誕交換禮物）", key="c_room_name")
            host_name = st.text_input("房主姓名（房主亦一同參與）", key="c_host_name")
            host_pass = st.text_input("設定房主專用密碼（4位數數字）", type="password", max_chars=4, key="c_host_pass")

            if st.button("建立房間並直接進入 🚀", type="primary", key="btn_create_gift_room"):
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
                    st.rerun()

        else:
            st.subheader("手動輸入房號進入")
            input_rid = st.text_input("請輸入 6 位數房號：", key="c_input_rid").strip()
            if st.button("進入房間", key="btn_join_gift_room"):
                if not input_rid:
                    st.error("請輸入房號！")
                else:
                    doc = db.collection("rooms").document(input_rid).get()
                    if not doc.exists:
                        st.error("找不到此房號，請確認後重新輸入！")
                    else:
                        st.session_state["current_gift_room"] = input_rid
                        st.rerun()

# -------------------- TAB 2: 部門抽獎 --------------------
with tab2:
    st.header("🎉 部門現場抽獎")

    if "current_lotto_room" in st.session_state and st.session_state["current_lotto_room"]:
        l_room_id = st.session_state["current_lotto_room"]
        l_doc_ref = db.collection("lottery_rooms").document(l_room_id)
        l_doc = l_doc_ref.get()

        if not l_doc.exists:
            st.error("抽獎房不存在！")
            if st.button("返回", key="back_lotto_hall"):
                del st.session_state["current_lotto_room"]
                st.rerun()
        else:
            l_room = l_doc.to_dict()
            l_host = l_room.get("host_name", "房主")
            st.info(f"📍 活動：**{l_room['room_name']}** ｜ 房號：**{l_room['room_id']}** ｜ 房主：**{l_host}**")

            if l_room["status"] == "waiting":
                st.subheader("👥 現場簽到抽獎池")
                st.write(f"目前名單（共 {len(l_room['members'])} 人）：")
                st.success("、".join(l_room["members"]))

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 刷新名單", key="ref_lotto"):
                        st.rerun()
                with col2:
                    if st.button("🚪 退出房間", key="exit_lotto"):
                        del st.session_state["current_lotto_room"]
                        st.rerun()

                st.markdown("---")
                l_join_name = st.text_input("輸入名字簽到：", key="l_join_name").strip()
                if st.button("簽到加入抽獎", key="btn_confirm_join_lotto"):
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
                    v_l_host_pass = st.text_input("請輸入房主管理密碼：", type="password", key="vl_h_pass")
                    draw_num = st.number_input("抽出幾個人？", min_value=1, max_value=max(1, len(l_room["members"])), value=1, step=1, key="lotto_draw_num")
                    if st.button("確認開獎 🎊", type="primary", key="btn_lotto_start_draw"):
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

                if st.button("🚪 退出房間（回首頁）", key="exit_lotto_fin"):
                    del st.session_state["current_lotto_room"]
                    st.rerun()

    else:
        # 部門抽獎的歷史清單卡片
        with st.expander("📜 查看過去歷史抽獎活動", expanded=False):
            search_lotto = db.collection("lottery_rooms").stream()
            all_lottos = [doc.to_dict() for doc in search_lotto]
            if all_lottos:
                for al in all_lottos:
                    l_stat = "✅ 已開獎" if al.get("status") == "finished" else "⏳ 進行中"
                    with st.container(border=True):
                        st.markdown(f"**🎉 {al.get('room_name')}**（房號：`{al['room_id']}`）- {l_stat}")
                        if st.button("查看此抽獎結果 👉", key=f"btn_l_{al['room_id']}"):
                            st.session_state["current_lotto_room"] = al["room_id"]
                            st.rerun()
            else:
                st.info("尚無歷史抽獎紀錄。")

        st.markdown("---")
        l_action = st.radio("選擇操作", ["建立抽獎房", "手動輸入房號進入"], horizontal=True, key="l_action_radio")

        if l_action == "建立抽獎房":
            st.subheader("建立現場抽獎房")
            new_l_name = st.text_input("抽獎活動名稱（如：會計部尾牙）", key="nl_name")
            new_l_host = st.text_input("房主姓名", key="nl_host")
            new_l_pass = st.text_input("設定房主專用密碼（4位數數字）", type="password", max_chars=4, key="nl_pass")

            if st.button("建立房間並直接進入 🚀", type="primary", key="btn_create_lotto_room"):
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
                    st.rerun()
        else:
            st.subheader("手動輸入房號進入")
            input_l_id = st.text_input("請輸入 6 位數抽獎房號：", key="inl_id").strip()
            if st.button("進入抽獎房", key="btn_join_lotto_room"):
                if not input_l_id:
                    st.error("請輸入房號！")
                else:
                    doc = db.collection("lottery_rooms").document(input_l_id).get()
                    if not doc.exists:
                        st.error("找不到此抽獎房號！")
                    else:
                        st.session_state["current_lotto_room"] = input_l_id
                        st.rerun()
