// Cache compiled functions, never report data. Each application process owns its renderer.
export function createEmailRenderer({ loadTemplates }) {
  let templateLoad;
  return async (report) => {
    templateLoad ??= loadTemplates().catch((error) => {
      templateLoad = undefined;
      throw error;
    });
    const { renderSubject, renderText, renderHtml } = await templateLoad;
    return {
      subject: renderSubject(report).trim(),
      text: renderText(report).trim(),
      html: renderHtml(report),
    };
  };
}
