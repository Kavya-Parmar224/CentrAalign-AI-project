import React, { useState } from 'react';
import { HelpCircle } from 'lucide-react';

export default function ApprovalModal({ question, onSubmit }) {
  const [answer, setAnswer] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(answer);
  };

  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-[#1a1d2e] border border-[#2a2d3e] rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden animate-fade-in">
        <div className="bg-gradient-to-r from-purple-600 to-blue-600 p-6 text-white flex items-start gap-4">
          <div className="bg-white/20 p-2 rounded-full">
            <HelpCircle className="w-8 h-8" />
          </div>
          <div>
            <h2 className="text-xl font-bold">🤔 AI Agent Needs Input</h2>
            <p className="text-purple-100 text-sm mt-1">The agent cannot proceed without your clarification.</p>
          </div>
        </div>
        
        <div className="p-6">
          <div className="bg-[#0f1117] p-4 rounded-lg text-gray-200 text-sm border border-[#2a2d3e] mb-6">
            {question?.question || "Please provide authorization or additional details."}
            {question?.context && (
              <div className="mt-2 pt-2 border-t border-[#2a2d3e] text-[#8892a4] text-xs">
                Context: {question.context}
              </div>
            )}
          </div>

          
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <input
              type="text"
              autoFocus
              className="w-full bg-[#0f1117] text-white border border-[#2a2d3e] rounded-lg p-3 text-sm focus:outline-none focus:border-purple-500 transition-colors placeholder-[#5c677d]"
              placeholder="Type your answer here..."
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
            />
            <button
              type="submit"
              disabled={!answer.trim()}
              className="w-full py-2.5 rounded-lg font-medium bg-white text-gray-900 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Submit Answer
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
