import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import random
import json

# ==================== 1. 初始化 Firebase ====================
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        # 優先讀取雲端 Streamlit Secrets，本機讀取 serviceAccountKey.json
        if "firebase" in st.secrets:
            key_dict = dict(st.secrets["firebase"])
            cred = credentials.Certificate(key_dict)
        else:
            cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

# ==================== 2. 演算法與工具函式 ====================
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

# ==================== 3. 介面設計 ====================
st.set_page_config(page_title="活動抽獎與交換禮物", layout="centered", page_icon="🎁")
st.title("🎁 活動抽獎 & 交換禮物系統")

tab1, tab2 = st.tabs(["🎄 交換禮物專用", "🎉 部門抽獎專用"])

# -------------------- TAB 1: 交換禮物 --------------------
with tab1:
    st.header("交換禮物房間")
    action = st.radio("選擇操作", ["加入/查看現有房間", "建立新房間"], horizontal=True, key="gift_action")
    
    # --- 建立房間 ---
    if action == "建立新房間":
        st.subheader("建立交換禮物房間")
        room_name = st.text_input("房間名稱（如：2026 大學聖誕趴）", key="new_gift_name")
        host_name = st.text_input("房主姓名（房主也會一起參與）", key="new_gift_host")
        host_passcode = st.text_input("房主防窺密碼（4位數數字）", type="password", max_chars=4, key="new_gift_pass")
        
        if st.button("建立房間並產生房號", type="primary"):
            if not room_name.strip() or not host_name.strip() or not host_passcode.strip():
                st.error("請完整填寫房名、房主名字與密碼！")
            else:
                room_id = str(random.randint(100000, 999999))
                room_ref = db.collection("rooms").document(room_id)
                room_ref.set({
                    "room_id": room_id,
                    "room_name": room_name.strip(),
                    "type": "gift",
                    "status": "waiting",
                    "host_name": host_name.strip(),
                    "members": [host_name.strip()],
                    "passcodes": {host_name.strip(): host_passcode.strip()},
                    "pairs": {}
                })
                st.success(f"房間建立成功！房號為：【{room_id}】")
                st.info("請將房號發給朋友，讓大家進入房間輸入名字！")

    # --- 加入 / 查看房間 ---
    else:
        st.subheader("進入房間")
        room_id_input = st.text_input("請輸入 6 位數房號：", key="join_gift_room_id").strip()
        
        if room_id_input:
            room_ref = db.collection("rooms").document(room_id_input)
            room_doc = room_ref.get()
            
            if not room_doc.exists:
                st.error("找不到此房號，請確認後重新輸入！")
            else:
                room = room_doc.to_dict()
                if room.get("type") != "gift":
                    st.warning("此房間不是交換禮物房間，請至抽獎分頁輸入！")
                else:
                    st.markdown(f"### 📍 房間：{room['room_name']}（房號：{room['room_id']}）")
                    
                    # 狀態 A：等待開獎（現場簽到中）
                    if room["status"] == "waiting":
                        st.info("目前狀態：成員簽到中...")
                        st.write(f"**已加入名單（共 {len(room['members'])} 人）：**")
                        st.write("、".join(room["members"]))
                        
                        st.markdown("#### 👤 報名加入")
                        join_name = st.text_input("輸入你的名字：", key="join_gift_user_name").strip()
                        join_pass = st.text_input("設定你的 4 位數防窺密碼：", type="password", max_chars=4, key="join_gift_user_pass").strip()
                        
                        if st.button("確認簽到加入"):
                            if not join_name or not join_pass:
                                st.error("名字與密碼不能為空！")
                            elif join_name in room["members"]:
                                st.warning("這個名字已經在名單中囉！")
                            else:
                                room["members"].append(join_name)
                                room["passcodes"][join_name] = join_pass
                                room_ref.update({
                                    "members": room["members"],
                                    "passcodes": room["passcodes"]
                                })
                                st.success("加入成功！")
                                st.rerun()

                        # 房主專用控制區
                        st.markdown("---")
                        st.markdown("#### 👑 房主專區")
                        if st.button("人到齊了，開始配對開獎！", type="primary"):
                            if len(room["members"]) < 2:
                                st.error("至少需要 2 個人才能配對！")
                            else:
                                final_pairs = derangement_shuffle(room["members"])
                                room_ref.update({
                                    "status": "finished",
                                    "pairs": final_pairs
                                })
                                st.success("配對完成！所有人現在可以查看對象了！")
                                st.rerun()

                    # 狀態 B：已完成配對（隨時 / 隔年回溯看結果）
                    elif room["status"] == "finished":
                        st.success("🎉 配對已完成！本活動紀錄已永久保存。")
                        st.markdown("#### 🎁 查看我抽到誰（防偷看保護）")
                        
                        my_name = st.selectbox("選擇你的名字：", ["-- 請選擇 --"] + sorted(room["members"]))
                        my_pass = st.text_input("輸入當初設定的防窺密碼：", type="password", key="view_gift_pass")
                        
                        if st.button("揭曉我的送禮對象 🎯"):
                            correct_pass = room["passcodes"].get(my_name)
                            if my_name == "-- 請選擇 --":
                                st.warning("請先選擇你的名字！")
                            elif my_pass != correct_pass:
                                st.error("密碼錯誤，請重新輸入！")
                            else:
                                target = room["pairs"].get(my_name)
                                st.balloons()
                                st.markdown(f"### ✨ **{my_name}**，你抽到的是：👉 **{target}** 👈")
                                st.caption("記好後可重整網頁或選回空白，避免旁人看見。")

# -------------------- TAB 2: 部門抽獎 --------------------
with tab2:
    st.header("部門現場抽獎房間")
    lottery_action = st.radio("選擇操作", ["加入/查看抽獎房間", "建立新抽獎房間"], horizontal=True, key="lottery_action")

    # --- 建立抽獎房間 ---
    if lottery_action == "建立新抽獎房間":
        st.subheader("建立抽獎房間")
        l_room_name = st.text_input("抽獎活動名稱（如：2026 會計部尾牙抽獎）", key="new_l_name")
        l_host_name = st.text_input("房主姓名（房主亦會一同參與抽獎）", key="new_l_host")
        
        if st.button("建立抽獎房並產生房號", type="primary"):
            if not l_room_name.strip() or not l_host_name.strip():
                st.error("請填寫活動名稱與房主名字！")
            else:
                l_room_id = str(random.randint(100000, 999999))
                l_room_ref = db.collection("lottery_rooms").document(l_room_id)
                l_room_ref.set({
                    "room_id": l_room_id,
                    "room_name": l_room_name.strip(),
                    "host_name": l_host_name.strip(),
                    "status": "waiting",
                    "members": [l_host_name.strip()],
                    "winners": [],
                    "draw_count": 0
                })
                st.success(f"抽獎房間建立成功！房號為：【{l_room_id}】")
                st.info("請讓同事在自己手機輸入此房號簽到！")

    # --- 進入抽獎房間 ---
    else:
        st.subheader("進入抽獎房間")
        l_room_id_input = st.text_input("請輸入 6 位數抽獎房號：", key="join_l_room_id").strip()
        
        if l_room_id_input:
            l_room_ref = db.collection("lottery_rooms").document(l_room_id_input)
            l_room_doc = l_room_ref.get()
            
            if not l_room_doc.exists:
                st.error("找不到此抽獎房號！")
            else:
                l_room = l_room_doc.to_dict()
                st.markdown(f"### 📍 抽獎房：{l_room['room_name']}（房號：{l_room['room_id']}）")
                
                # 等待簽到中
                if l_room["status"] == "waiting":
                    st.info("簽到中... 大家請在下方輸入名字加入抽獎池")
                    st.write(f"**目前參與全員（含房主共 {len(l_room['members'])} 人）：**")
                    st.write("、".join(l_room["members"]))
                    
                    l_join_name = st.text_input("輸入你的名字簽到：", key="join_l_user_name").strip()
                    if st.button("簽到加入抽獎"):
                        if not l_join_name:
                            st.error("名字不能為空！")
                        elif l_join_name in l_room["members"]:
                            st.warning("你已經在名單中囉！")
                        else:
                            l_room["members"].append(l_join_name)
                            l_room_ref.update({"members": l_room["members"]})
                            st.success("簽到成功！")
                            st.rerun()

                    # 房主開獎區
                    st.markdown("---")
                    st.markdown("#### 👑 房主開獎控制")
                    draw_num = st.number_input(
                        "抽出幾個人？",
                        min_value=1,
                        max_value=max(1, len(l_room["members"])),
                        value=1,
                        step=1
                    )
                    if st.button("確認開獎 🎊", type="primary"):
                        if len(l_room["members"]) == 0:
                            st.error("名單內沒有人！")
                        else:
                            winners = random.sample(l_room["members"], int(draw_num))
                            l_room_ref.update({
                                "status": "finished",
                                "winners": winners,
                                "draw_count": int(draw_num)
                            })
                            st.success("開獎成功！")
                            st.rerun()

                # 已開獎（全員同步看榜 / 事後回溯）
                elif l_room["status"] == "finished":
                    st.balloons()
                    st.success(f"🎉 開獎完畢！共抽出 {len(l_room['winners'])} 位幸運得主：")
                    for idx, w in enumerate(l_room["winners"], start=1):
                        st.markdown(f"### 🏆 第 {idx} 名：{w}")
                    
                    with st.expander("檢視當次抽獎所有參與者名單"):
                        st.write("、".join(l_room["members"]))
