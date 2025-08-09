import React from 'react';

function RelatedSectionsSidebar({ sections, recommendations, onSectionSelect, isLoading }) {
  return (
    <div className="mt-6">
      <h2 className="text-lg font-bold text-gray-800 mb-2">Document Sections</h2>
      <ul className="mb-6">
        {sections.map((section, index) => (
          <li
            key={index}
            onClick={() => onSectionSelect(index)}
            className="cursor-pointer p-2 rounded-md hover:bg-gray-200"
          >
            {section.title} <span className="text-sm text-gray-500">(p. {section.page_number})</span>
          </li>
        ))}
      </ul>

      <h2 className="text-lg font-bold text-gray-800 mb-2">Related Sections</h2>
      {isLoading ? (
        <p>Finding related sections...</p>
      ) : (
        <ul>
          {recommendations.map((rec, index) => (
            <li key={index} className="p-2 border-b border-gray-200">
              <p className="font-semibold">{rec.section_title}</p>
              <p className="text-sm text-gray-500">Page: {rec.page_number}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default RelatedSectionsSidebar;