import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Renders model output as markdown. No raw-HTML plugin, so model text can never
// inject markup. Links open in a new tab.
export function Markdown({ children }: { children: string }) {
  return (
    <div className="md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ node, ...props }) => <a target="_blank" rel="noreferrer" {...props} />,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
