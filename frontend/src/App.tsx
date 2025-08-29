import React, { useState } from "react";

const App: React.FC = () => {
  const [text, setText] = useState("");
  const [guidance, setGuidance] = useState("");
  const [provider, setProvider] = useState("openai");
  const [apiKey, setApiKey] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [speakerNotes, setSpeakerNotes] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setDownloadUrl(null);
    if (!file) {
      setError("Please upload a .pptx/.potx template");
      return;
    }
    setLoading(true);
    try {
      const form = new FormData();
      form.append("template", file);
      form.append("text", text);
      if (guidance) form.append("guidance", guidance);
      if (provider) form.append("provider", provider);
      if (apiKey) form.append("api_key", apiKey); // Never stored; only forwarded to backend per request
      form.append("speaker_notes", String(speakerNotes));

      const resp = await fetch(import.meta.env.VITE_API_URL || "http://localhost:8000/api/generate", {
        method: "POST",
        body: form,
      });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data.detail || `Request failed (${resp.status})`);
      }
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      setDownloadUrl(url);
    } catch (err: any) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-3xl mx-auto bg-white rounded-2xl shadow p-6 space-y-6">
        <h1 className="text-2xl font-bold">Your Text, Your Style → Auto PowerPoint</h1>
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Bulk text or Markdown</label>
            <textarea
              className="w-full h-48 border rounded-lg p-3"
              placeholder="Paste long-form prose or markdown..."
              value={text}
              onChange={(e) => setText(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Optional one-line guidance</label>
            <input
              className="w-full border rounded-lg p-2"
              placeholder='e.g., "turn into an investor pitch deck"'
              value={guidance}
              onChange={(e) => setGuidance(e.target.value)}
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">LLM provider</label>
              <select className="w-full border rounded-lg p-2" value={provider} onChange={(e) => setProvider(e.target.value)}>
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
                <option value="gemini">Gemini</option>
                <option value="">(No LLM — heuristic)</option>
              </select>
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-1">API key (never stored)</label>
              <input
                type="password"
                className="w-full border rounded-lg p-2"
                placeholder="Paste your API key (optional if using heuristic)"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">PowerPoint template (.pptx/.potx)</label>
            <input
              type="file"
              accept=".pptx,.potx"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
          </div>

          <label className="inline-flex items-center space-x-2">
            <input type="checkbox" checked={speakerNotes} onChange={(e) => setSpeakerNotes(e.target.checked)} />
            <span>Add speaker notes (if LLM used)</span>
          </label>

          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 rounded-xl bg-black text-white disabled:opacity-60"
            >
              {loading ? "Generating..." : "Generate .pptx"}
            </button>
            {downloadUrl && (
              <a href={downloadUrl} download="generated.pptx" className="text-blue-600 underline">
                Download generated.pptx
              </a>
            )}
          </div>
          {error && <div className="text-red-600 text-sm">{error}</div>}
          <p className="text-xs text-gray-500">
            Your API key is sent directly to your selected provider via the backend for this request only. It is never logged or stored.
          </p>
        </form>
      </div>
    </div>
  );
};

export default App;
