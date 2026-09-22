"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { webOidcEnabled } from "@/lib/auth-mode";
import { QueryError } from "./query-error";
import { Button } from "./ui/button";

export function ProfilePage({ reauthenticated }: { reauthenticated: boolean }) {
  const router = useRouter();
  const client = useQueryClient();
  const [confirmation, setConfirmation] = useState("");
  const user = useQuery({ queryKey: ["me"], queryFn: () => api.me() });
  const update = useMutation({
    mutationFn: (form: FormData) =>
      api.updateMe({
        display_name: String(form.get("display_name")).trim(),
        timezone: String(form.get("timezone")).trim(),
        locale: String(form.get("locale")).trim(),
      }),
    onSuccess: async (value) => {
      await client.setQueryData(["me"], value);
    },
  });
  const exportData = useMutation({
    mutationFn: () => api.exportData(),
    onSuccess: (data) => {
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json;charset=utf-8",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `tovia-export-${new Date().toISOString().slice(0, 10)}.json`;
      link.click();
      URL.revokeObjectURL(url);
    },
  });
  const removeAccount = useMutation({
    mutationFn: () => api.deleteAccount(),
    onSuccess: () => router.push("/sign-out"),
  });

  if (user.isPending) return <p role="status">正在读取账户资料…</p>;
  if (user.error)
    return <QueryError error={user.error} retry={() => void user.refetch()} />;

  return (
    <section className="max-w-3xl space-y-6">
      <header className="page-heading">
        <div>
          <p className="eyebrow">PROFILE</p>
          <h1>我的账户</h1>
          <p className="muted mt-2">
            查看和维护账户资料，随时带走自己的旅行数据。
          </p>
        </div>
      </header>

      <form
        className="panel space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          update.mutate(new FormData(event.currentTarget));
        }}
      >
        <h2 className="text-xl">基本资料</h2>
        <p className="muted">账户 ID：{user.data.id}</p>
        <div className="form-grid">
          <label className="field">
            显示名称
            <input
              name="display_name"
              required
              maxLength={100}
              defaultValue={user.data.display_name}
            />
          </label>
          <label className="field">
            默认时区
            <input
              name="timezone"
              required
              placeholder="Asia/Shanghai"
              defaultValue={user.data.timezone}
            />
          </label>
          <label className="field">
            界面语言
            <select name="locale" defaultValue={user.data.locale}>
              <option value="zh-CN">简体中文</option>
              <option value="zh-TW">繁體中文</option>
              <option value="en">English</option>
            </select>
          </label>
        </div>
        {update.error && (
          <p role="alert" className="error-message">
            {update.error.message}
          </p>
        )}
        {update.isSuccess && (
          <p role="status" className="text-sm">
            资料已保存。
          </p>
        )}
        <Button disabled={update.isPending}>
          {update.isPending ? "保存中…" : "保存资料"}
        </Button>
      </form>

      <section className="panel space-y-3">
        <h2 className="text-xl">数据导出</h2>
        <p className="muted">
          下载包含旅行、旅行日、到访、活动、地点与愿望清单的 JSON 文件；记录 ID
          和关联关系会保留。
        </p>
        {exportData.error && (
          <p role="alert" className="error-message">
            {exportData.error.message}
          </p>
        )}
        <Button
          variant="outline"
          disabled={exportData.isPending}
          onClick={() => exportData.mutate()}
        >
          {exportData.isPending ? "正在准备导出…" : "下载我的数据"}
        </Button>
      </section>

      <section className="panel space-y-4 border-red-200">
        <h2 className="text-xl">删除账户</h2>
        <p className="muted">
          删除会移除 Logto 登录身份及 Tovia
          中的账户资料、旅行和关联记录，无法撤销。建议先下载数据副本。
        </p>
        {!webOidcEnabled ? (
          <p className="muted">
            当前是本地开发身份，账户删除仅在 Logto 登录模式下开放。
          </p>
        ) : !reauthenticated ? (
          <Button
            variant="outline"
            onClick={() => router.push("/sign-in?reauth=delete")}
          >
            重新登录以继续
          </Button>
        ) : (
          <div className="space-y-3">
            <label className="field max-w-sm">
              输入 DELETE 确认
              <input
                value={confirmation}
                onChange={(event) => setConfirmation(event.target.value)}
                autoComplete="off"
              />
            </label>
            {removeAccount.error && (
              <p role="alert" className="error-message">
                {removeAccount.error.message}
              </p>
            )}
            <Button
              variant="outline"
              className="border-red-300 text-red-700 hover:bg-red-50"
              disabled={confirmation !== "DELETE" || removeAccount.isPending}
              onClick={() => removeAccount.mutate()}
            >
              {removeAccount.isPending ? "正在删除…" : "永久删除账户和数据"}
            </Button>
          </div>
        )}
      </section>
    </section>
  );
}
