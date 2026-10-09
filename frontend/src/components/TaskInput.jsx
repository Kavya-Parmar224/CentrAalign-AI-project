import React, { useState } from 'react';

export default function TaskInput({ onSubmit, onStop, isRunning, status }) {
  const [text, setText] = useState('');

  const samples = [
    "Find the open high-priority ticket, look up the user's manager via the API, and write a summary file.",
    "Check the onboarding ticket, navigate to the provisioning page, grant them GitHub access, and mark the ticket as resolved.",
    "Get all open tickets via the API and summarize the current workload."
  ];

  const statusColors = {
    Idle: 'bg-gray-600',
    Planning: 'bg-yellow-600',
    Running: 'bg-blue-600 animate-pulse',
    Verifying: 'bg-purple-600 animate-pulse',
    Done: 'bg-green-600',
    Failed: 'bg-red-600'
  };

  return (
    <div className="bg-[#1a1d2e] rounded-xl p-5 shadow-lg border border-[#2a2d3e]">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          New Task
        </h2>
        <div className={`px-3 py-1 rounded-full text-xs font-medium text-white ${statusColors[status] || 'bg-gray-600'}`}>
          {status}
        </div>
      </div>
      
      <textarea
        className="w-full bg-[#0f1117] text-white border border-[#2a2d3e] rounded-lg p-3 text-sm focus:outline-none focus:border-purple-500 transition-colors mb-4 resize-none placeholder-[#5c677d]"
        rows={4}
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={isRunning}
        placeholder={"Describe the task for the AI worker...\n\nExample: Find the latest invoice from Company X, extract the amount and due date, enter it into our system, and confirm it was saved."}
      />

      <div className="mb-4 flex flex-wrap gap-2">
        {samples.map((sample, i) => (
          <button
            key={i}
            onClick={() => setText(sample)}
            disabled={isRunning}
            className="text-xs bg-[#22263b] hover:bg-[#2c3149] text-[#8892a4] hover:text-white px-2 py-1 rounded border border-[#2a2d3e] transition-colors text-left"
          >
            {sample}
          </button>
        ))}
      </div>

      {isRunning ? (
        <button
          onClick={onStop}
          className="w-full py-2 rounded-lg font-medium transition-all bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-900/20"
        >
          Stop Agent
        </button>
      ) : (
        <button
          onClick={() => onSubmit(text)}
          disabled={!text.trim()}
          className={`w-full py-2 rounded-lg font-medium transition-all ${
            !text.trim()
              ? 'bg-[#2a2d3e] text-[#5c677d] cursor-not-allowed'
              : 'bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-white shadow-lg shadow-purple-900/20'
          }`}
        >
          Start Task
        </button>
      )}
    </div>
  );
}
