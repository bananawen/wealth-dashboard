# Authentication and Access Model

## 結論

本專案目前以單一使用者部署為前提。

- 第一個註冊帳號是 owner 帳號。
- owner 帳號在資料表中的 `users.role` 會是 `admin`。
- `admin` 角色只用來開啟系統管理工具，不代表產品要支援多使用者協作。

## 目前規則

### 1. 註冊

- API：`POST /auth/register`
- 實作位置：`backend/app/routers/auth.py`
- 規則：
  - 如果 `users` 資料表目前沒有任何帳號，第一個註冊帳號會寫入 `role='admin'`
  - 之後新增的帳號預設寫入 `role='user'`

### 2. 登入

- API：`POST /auth/login`
- JWT payload 目前包含：
  - `sub`
  - `user_id`
  - `role`

### 3. 系統管理頁

- 前端路由：`/admin`
- 後端保護：
  - `backend/app/routers/auth.py` 的 `require_admin_user`
- 規則：
  - `users.role='admin'` 才能使用系統管理功能
  - 非 `admin` 帳號會收到 `403` 與 `需要系統管理權限`

## UI 呈現原則

- Login / Register 頁面明確告知第一個註冊帳號會成為 owner。
- Dashboard 頂部會顯示目前是：
  - `Owner / 系統管理已啟用`
  - 或 `單一使用者模式`
- Admin 頁面明確標示這是 owner 的系統工具區。

## 部署假設

- 使用者模型：單一使用者
- 主要用途：個人投資資料管理
- `admin` 的意義：保護備份、版本、爬蟲、Audit Log 等系統操作

## 風險

- 目前 schema 仍保留 `users`、`user_id` 等多使用者痕跡，主要是沿用既有資料結構與查詢欄位。
- 如果未來真的要支援多使用者，不能只靠目前 UI 文案，必須重新檢討資料隔離、帳號生命周期、管理流程與稽核模型。

## 建議

- 短期：維持單一使用者部署，讓 UI、文件與錯誤訊息一致。
- 中期：把 owner 帳號維運流程寫進部署文件，避免未來只能靠資料庫手動判讀。
- 長期：若確定永遠不做多使用者，再評估是否收斂 `user_id` 等歷史結構。
