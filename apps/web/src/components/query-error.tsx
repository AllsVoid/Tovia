import { Button } from "./ui/button";
export function QueryError({
  error,
  retry,
}: {
  error: Error | null;
  retry?: () => void;
}) {
  return (
    <div role="alert" className="panel">
      <p className="error-message">
        {error?.message ?? "读取失败，请稍后重试。"}
      </p>
      {retry && (
        <Button variant="outline" onClick={retry}>
          重试
        </Button>
      )}
    </div>
  );
}
