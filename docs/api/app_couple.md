### `backend/application/couples/errors.py` — 情侣关系异常

```python
class CoupleError(Exception)
```

- 绑定 / 解绑 / 冻结相关业务失败时抛出

---

### `backend/application/couples/policies.py` — 关系规则判断

```python
def ensure_can_send_bind_request(from_user_id: str, to_user_id: str) -> None
```

- 业务校验：
  - 不能给自己发绑定请求
  - 目标用户必须存在
  - 双方都不能已有 `active` / `frozen` / `pending_bind` 关系
- 校验失败时抛 `CoupleError`

```python
def ensure_can_start_uncouple(user_id: str) -> None
```

- 发起冻结式解绑前的校验
- 要求当前存在绑定关系
- 若已处于冻结期则抛 `CoupleError`

```python
def ensure_can_confirm_uncouple(user_id: str) -> None
```

- 发起“双方同意立即销毁”前的校验
- 要求当前存在绑定关系

```python
def ensure_can_request_cancel_uncouple(user_id: str) -> None
```

- 发起“撤回冻结”请求前的校验
- 要求当前必须处于 `frozen`
- 若已有待回应请求则抛 `CoupleError`

```python
def ensure_can_confirm_cancel_uncouple(user_id: str) -> None
```

- 同意撤回冻结前的校验
- 要求当前必须处于 `frozen`
- 要求存在待回应请求
- 调用者必须是请求接收方

```python
def ensure_can_reject_cancel_uncouple(user_id: str) -> None
```

- 拒绝撤回冻结前的校验
- 规则与 `ensure_can_confirm_cancel_uncouple()` 一致

```python
def ensure_can_withdraw_cancel_request(user_id: str) -> None
```

- 发起方撤回自己的撤回请求前的校验
- 要求当前必须处于 `frozen`
- 要求存在待回应请求
- 调用者必须是请求发起方

---

### `backend/application/couples/binding.py` — 绑定流程

```python
def send_bind_request(from_user_id: str, to_user_id: str) -> Couple
```

- 先执行 `ensure_can_send_bind_request()`
- 校验通过后调用 `couples_repo.create_couple_request()`
- 返回新建的 `Couple`

```python
def accept_bind(couple_id: str) -> None
```

- 接受绑定请求
- 调用 `accept_couple_request()`

```python
def reject_bind(couple_id: str) -> None
```

- 拒绝绑定请求
- 调用 `reject_couple_request()`

---

### `backend/application/couples/uncoupling.py` — 解绑与冻结期

```python
def start_uncouple(user_id: str) -> None
```

- 单方发起分手
- 要求当前必须处于 `active` 关系中
- 通过后将 couple 更新为：
  - `couple_status = "frozen"`
  - 记录 `uncouple_initiated_by`
  - 记录 `uncouple_initiated_at`
  - 设置 `freeze_ends_at = now + 90 天`

```python
def confirm_uncouple(user_id: str) -> None
```

- 双方同意立即解绑
- 要求当前必须存在绑定关系
- 通过后将 `both_agreed_uncouple = True`
- 随后立即调用 `destroy_couple_data()`，销毁 sessions、reports 并解绑双方用户

```python
def request_cancel_uncouple(user_id: str) -> None
```

- 冻结期内任一方都可发起
- 先执行 `ensure_can_request_cancel_uncouple()`
- 成功后写入：
  - `cancel_uncouple_requested_by`
  - `cancel_uncouple_requested_at`

```python
def confirm_cancel_uncouple(user_id: str) -> None
```

- 由请求接收方同意撤回冻结
- 先执行 `ensure_can_confirm_cancel_uncouple()`
- 成功后将关系恢复为 `active`
- 同时清空冻结相关字段与撤回请求字段：
  - `uncouple_initiated_by`
  - `uncouple_initiated_at`
  - `freeze_ends_at`
  - `cancel_uncouple_requested_by`
  - `cancel_uncouple_requested_at`

```python
def reject_cancel_uncouple(user_id: str) -> None
```

- 由请求接收方拒绝撤回冻结
- 先执行 `ensure_can_reject_cancel_uncouple()`
- 仅清空撤回请求字段，关系仍保持 `frozen`

```python
def withdraw_cancel_request(user_id: str) -> None
```

- 由请求发起方主动收回自己的撤回请求
- 先执行 `ensure_can_withdraw_cancel_request()`
- 仅清空撤回请求字段，关系仍保持 `frozen`

```python
def is_frozen(user_id: str) -> bool
```

- 判断当前用户所在关系是否处于冻结期
- UI 层用它决定是否只读
