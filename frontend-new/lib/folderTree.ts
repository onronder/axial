/**
 * Folder Tree Utility
 * 
 * Builds a virtual folder hierarchy from flat document data.
 * Used by the Knowledge Base Browser for folder navigation.
 */

import { Document } from "@/types";

// =============================================================================
// TYPES
// =============================================================================

/**
 * Represents a folder node in the virtual tree
 */
export interface FolderNode {
  id: string;
  name: string;
  path: string;
  type: "folder";
  children: TreeNode[];
  documentCount: number;
  sourceType?: string;
}

/**
 * Represents a document (file) node in the virtual tree
 */
export interface DocumentNode {
  id: string;
  name: string;
  path: string;
  type: "file";
  document: Document;
}

/**
 * Union type for tree nodes
 */
export type TreeNode = FolderNode | DocumentNode;

/**
 * Type guard for folder nodes
 */
export function isFolderNode(node: TreeNode): node is FolderNode {
  return node.type === "folder";
}

/**
 * Type guard for document nodes
 */
export function isDocumentNode(node: TreeNode): node is DocumentNode {
  return node.type === "file";
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Generate a stable hash for a path string
 */
function hashPath(path: string): string {
  let hash = 0;
  for (let i = 0; i < path.length; i++) {
    const char = path.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return Math.abs(hash).toString(36);
}

/**
 * Format source type to display name
 */
function formatSourceName(sourceType: string): string {
  const names: Record<string, string> = {
    file_upload: "📁 Uploaded Files",
    google_drive: "🔷 Google Drive",
    notion: "📝 Notion",
    web: "🌐 Web Pages",
    onedrive: "☁️ OneDrive",
    sharepoint: "📊 SharePoint",
    dropbox: "📦 Dropbox",
    github: "🐙 GitHub",
    slack: "💬 Slack",
    s3: "🪣 Amazon S3",
    youtube: "▶️ YouTube",
    sftp: "🔐 SFTP",
    box: "📥 Box",
  };
  return names[sourceType] || sourceType.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase());
}

/**
 * Get path segments from a path string
 */
function getPathSegments(path: string): string[] {
  return path.split("/").filter(Boolean);
}

// =============================================================================
// TREE BUILDING
// =============================================================================

/**
 * Build a virtual folder tree from a flat list of documents.
 * 
 * Structure:
 * - Root: "All Documents"
 *   - Source folders (Google Drive, Notion, etc.)
 *     - Folder hierarchy based on document paths
 *       - Documents
 * 
 * @param documents - Array of documents to build tree from
 * @returns Root folder node containing the entire tree
 */
export function buildFolderTree(documents: Document[]): FolderNode {
  // Root node
  const root: FolderNode = {
    id: "root",
    name: "All Documents",
    path: "/",
    type: "folder",
    children: [],
    documentCount: documents.length,
  };

  if (documents.length === 0) {
    return root;
  }

  // Group documents by source type
  const bySource = new Map<string, Document[]>();
  
  for (const doc of documents) {
    const source = doc.sourceType || "file_upload";
    if (!bySource.has(source)) {
      bySource.set(source, []);
    }
    bySource.get(source)!.push(doc);
  }

  // Create source folders at root level
  for (const [source, docs] of bySource) {
    const sourceFolder: FolderNode = {
      id: `source-${source}`,
      name: formatSourceName(source),
      path: `/${source}`,
      type: "folder",
      children: [],
      documentCount: docs.length,
      sourceType: source,
    };

    // Build folder structure within each source
    buildSubtree(sourceFolder, docs);
    
    // Sort children: folders first, then files alphabetically
    sortChildren(sourceFolder);
    
    root.children.push(sourceFolder);
  }

  // Sort source folders by name
  root.children.sort((a, b) => a.name.localeCompare(b.name));

  return root;
}

/**
 * Build the subtree for a source folder
 */
function buildSubtree(parent: FolderNode, documents: Document[]): void {
  const folders = new Map<string, FolderNode>();
  
  for (const doc of documents) {
    // Get the path within this source
    const docPath = doc.path || doc.name;
    const segments = getPathSegments(docPath);
    
    // If no path or just filename, add directly to parent
    if (segments.length <= 1) {
      const docNode: DocumentNode = {
        id: doc.id,
        name: doc.name,
        path: docPath,
        type: "file",
        document: doc,
      };
      parent.children.push(docNode);
      continue;
    }

    // Build folder hierarchy
    let currentPath = parent.path;
    let currentFolder = parent;
    
    // Create folder nodes for each path segment (except the last which is the filename)
    for (let i = 0; i < segments.length - 1; i++) {
      const segment = segments[i];
      currentPath = `${currentPath}/${segment}`;
      
      if (!folders.has(currentPath)) {
        const folder: FolderNode = {
          id: `folder-${hashPath(currentPath)}`,
          name: segment,
          path: currentPath,
          type: "folder",
          children: [],
          documentCount: 0,
          sourceType: parent.sourceType,
        };
        folders.set(currentPath, folder);
        currentFolder.children.push(folder);
      }
      
      currentFolder = folders.get(currentPath)!;
    }
    
    // Add document to the deepest folder
    // Note: segments[segments.length - 1] is always truthy here because:
    // 1. getPathSegments uses filter(Boolean) which removes empty strings
    // 2. We only reach here when segments.length > 1
    const docNode: DocumentNode = {
      id: doc.id,
      name: segments[segments.length - 1],
      path: docPath,
      type: "file",
      document: doc,
    };
    currentFolder.children.push(docNode);
  }
  
  // Recursively sort all children and update counts
  updateCountsAndSort(parent);
}

/**
 * Recursively update document counts and sort children
 */
function updateCountsAndSort(folder: FolderNode): number {
  let count = 0;
  
  for (const child of folder.children) {
    if (isFolderNode(child)) {
      count += updateCountsAndSort(child);
    } else {
      count += 1;
    }
  }
  
  folder.documentCount = count;
  sortChildren(folder);
  
  return count;
}

/**
 * Sort children: folders first (alphabetically), then files (alphabetically)
 */
function sortChildren(folder: FolderNode): void {
  folder.children.sort((a, b) => {
    // Folders come first
    if (a.type !== b.type) {
      return a.type === "folder" ? -1 : 1;
    }
    // Then alphabetically by name (case-insensitive)
    return a.name.toLowerCase().localeCompare(b.name.toLowerCase());
  });
}

// =============================================================================
// TREE NAVIGATION
// =============================================================================

/**
 * Find a folder node by path in the tree
 * 
 * @param root - Root folder node
 * @param path - Path to find (e.g., "/google_drive/Projects/Q4")
 * @returns The folder node if found, null otherwise
 */
export function findFolderByPath(root: FolderNode, path: string): FolderNode | null {
  if (path === "/" || path === root.path) {
    return root;
  }

  const segments = getPathSegments(path);
  let current: FolderNode = root;

  for (const segment of segments) {
    const child = current.children.find(
      (c) => isFolderNode(c) && (c.name === segment || c.path.endsWith(`/${segment}`))
    );
    
    if (!child || !isFolderNode(child)) {
      return null;
    }
    
    current = child;
  }

  return current;
}

/**
 * Get breadcrumb trail for a path
 * 
 * @param root - Root folder node
 * @param path - Current path
 * @returns Array of breadcrumb items
 */
export interface BreadcrumbItem {
  id: string;
  name: string;
  path: string;
}

export function getBreadcrumbs(root: FolderNode, path: string): BreadcrumbItem[] {
  const breadcrumbs: BreadcrumbItem[] = [
    { id: root.id, name: root.name, path: root.path }
  ];

  if (path === "/" || path === root.path) {
    return breadcrumbs;
  }

  const segments = getPathSegments(path);
  let currentPath = "";
  let current: FolderNode = root;

  for (const segment of segments) {
    currentPath = `${currentPath}/${segment}`;
    
    const child = current.children.find(
      (c) => isFolderNode(c) && c.path === currentPath
    );
    
    if (child && isFolderNode(child)) {
      breadcrumbs.push({
        id: child.id,
        name: child.name,
        path: child.path,
      });
      current = child;
    } else {
      // Path segment not found as folder, try matching by name
      const byName = current.children.find(
        (c) => isFolderNode(c) && c.name === segment
      );
      if (byName && isFolderNode(byName)) {
        breadcrumbs.push({
          id: byName.id,
          name: byName.name,
          path: byName.path,
        });
        current = byName;
        currentPath = byName.path; // Update to actual path
      }
    }
  }

  return breadcrumbs;
}

/**
 * Search for documents and folders matching a query
 * 
 * @param root - Root folder node
 * @param query - Search query
 * @returns Filtered tree with matching items
 */
export function searchTree(root: FolderNode, query: string): TreeNode[] {
  if (!query.trim()) {
    return root.children;
  }

  const normalizedQuery = query.toLowerCase().trim();
  const results: TreeNode[] = [];

  function searchRecursive(node: TreeNode): void {
    const nameMatches = node.name.toLowerCase().includes(normalizedQuery);
    
    if (isFolderNode(node)) {
      // Include folder if name matches
      if (nameMatches) {
        results.push(node);
      }
      // Search children regardless
      for (const child of node.children) {
        searchRecursive(child);
      }
    } else {
      // Include document if name matches or document properties match
      if (nameMatches || 
          node.document.path?.toLowerCase().includes(normalizedQuery) ||
          node.document.sourceType?.toLowerCase().includes(normalizedQuery)) {
        results.push(node);
      }
    }
  }

  for (const child of root.children) {
    searchRecursive(child);
  }

  return results;
}

/**
 * Get all documents from a folder and its subfolders
 * 
 * @param folder - Folder to get documents from
 * @returns Array of all documents in the folder tree
 */
export function getAllDocumentsInFolder(folder: FolderNode): Document[] {
  const documents: Document[] = [];

  function collectDocuments(node: TreeNode): void {
    if (isDocumentNode(node)) {
      documents.push(node.document);
    } else {
      for (const child of node.children) {
        collectDocuments(child);
      }
    }
  }

  for (const child of folder.children) {
    collectDocuments(child);
  }

  return documents;
}

/**
 * Get document IDs from a folder (for bulk operations)
 */
export function getDocumentIdsInFolder(folder: FolderNode): string[] {
  return getAllDocumentsInFolder(folder).map(d => d.id);
}
