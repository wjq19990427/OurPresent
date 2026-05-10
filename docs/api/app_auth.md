### `backend/application/auth/errors.py` — 认证异常

```python
class AuthError(Exception)
```

- 注册 / 登录失败时抛出

---

### `backend/application/auth/commands.py` — 注册与登录

```python
def register(username: str, password: str) -> User
```

- 校验用户名和密码合法性：
  - 用户名长度 2-20
  - 密码至少 6 位
  - 用户名不能重复
- 校验通过后调用 `users_repo.create_user()`
- 返回 `User`

```python
def login(username: str, password: str) -> User
```

- 按用户名查询用户
- 校验密码
- 成功返回 `User`
- 失败抛 `AuthError`

---

### `backend/application/auth/tokens.py` — 登录 token 用例

```python
def create_auth_token(user_id: str) -> str
```

- 创建登录 token
- 内部调用 `tokens_repo.create_auth_token()`
- 对外只返回 token 字符串

```python
def validate_auth_token(token: str) -> User | None
```

- 先校验 token 是否存在且未过期
- 有效时再根据 `user_id` 取回 `User`
- 无效时返回 `None`

```python
def revoke_auth_token(token: str) -> None
```

- 撤销登录 token
- 退出登录时调用
