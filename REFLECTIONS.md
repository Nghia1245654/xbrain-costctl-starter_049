# Reflections — G11

## 1) Multi-account
Để chạy `costctl` cho ~100 AWS accounts, cần thêm cơ chế assume-role cross-account (ví dụ OrganizationAccountAccessRole hoặc role chuẩn do công ty quy định) và vòng lặp qua danh sách account (AWS Organizations hoặc file CSV). Output nên gom về một định dạng chuẩn (CSV/JSON) theo từng account + region, và có tổng hợp (summary) để so sánh/ưu tiên hành động.

## 3) `clean --apply` blast radius
Nếu lỡ chạy `clean --tag Environment=dev --apply` trong account dùng chung, mình muốn có “guardrails” như: allowlist account/OU, bắt buộc `--yes-i-understand` hoặc `--scope account-id`, và hiển thị preview + số lượng + danh sách resource trước khi thực thi (kèm confirm 2 bước). Ngoài ra nên áp dụng IAM policy hạn chế theo tag/namespace riêng của team để giảm khả năng xoá nhầm tài nguyên không thuộc quyền sở hữu.
