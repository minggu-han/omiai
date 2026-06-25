"""FastAPI 端点集成测试"""
import os
os.environ['OPENAI_API_KEY'] = 'sk-test'

from main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# 1. 创建会话
r = client.post('/api/session')
assert r.status_code == 200, f"创建会话失败: {r.status_code}"
sid = r.json()['session_id']
print(f'1. 创建会话: OK -> {sid}')

# 2. 分析
r = client.post('/api/analyze', json={
    'session_id': sid,
    'chat_history': [
        {'speaker': 'other', 'content': '今天好累啊'},
        {'speaker': 'me', 'content': '怎么了？'},
        {'speaker': 'other', 'content': '老板又加需求'}
    ],
    'user_persona': '内向理工男',
    'user_goal': '邀约见面'
})
assert r.status_code == 200, f"分析失败: {r.status_code}"
data = r.json()
assert data['is_interrupted'] == True
state = data['state']
assert 'analysis_report' in state
assert state.get('candidates')
print(f'2. 分析: OK (interrupted={data["is_interrupted"]}, candidates={len(state["candidates"])})')

# 3. 审核 - accept
r = client.post('/api/review', json={
    'session_id': sid,
    'decision': 'accept',
    'selected_index': 0
})
assert r.status_code == 200, f"审核失败: {r.status_code}"
data2 = r.json()
state2 = data2['state']
assert state2.get('final_reply')
assert state2.get('simulation')
print(f'3. 审核(accept): OK -> final_reply={"".join(state2["final_reply"][:40])}...')

# 4. 查询状态
r = client.get(f'/api/state/{sid}')
assert r.status_code == 200
assert r.json()['state'].get('final_reply')
print(f'4. 查询状态: OK')

# 5. 测试 reject 流程
r2 = client.post('/api/session')
sid2 = r2.json()['session_id']
client.post('/api/analyze', json={
    'session_id': sid2,
    'chat_history': [{'speaker': 'other', 'content': '在吗'}, {'speaker': 'me', 'content': '在的'}],
    'user_persona': '',
    'user_goal': ''
})
# reject 第一次
r = client.post('/api/review', json={'session_id': sid2, 'decision': 'reject', 'selected_index': 0})
assert r.status_code == 200
state_r = r.json()['state']
assert state_r['retry_count'] == 1
assert r.json()['is_interrupted'] == True
print(f'5. reject x1: OK (retry_count=1, interrupted=True)')

# reject 第二次
r = client.post('/api/review', json={'session_id': sid2, 'decision': 'reject', 'selected_index': 0})
state_r2 = r.json()['state']
assert state_r2['retry_count'] == 2
print(f'6. reject x2: OK (retry_count=2)')

# reject 第三次 → 应该达到上限
r = client.post('/api/review', json={'session_id': sid2, 'decision': 'reject', 'selected_index': 0})
state_r3 = r.json()['state']
assert state_r3['retry_count'] == 3
print(f'7. reject x3: OK (retry_count=3, should force exit)')

# 6. 健康检查
r = client.get('/api/health')
assert r.status_code == 200
print(f'8. 健康检查: OK')

print()
print('全部 API 端点测试通过!')
