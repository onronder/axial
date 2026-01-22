/**
 * Unit Tests for lib/folderTree.ts
 * 
 * Comprehensive tests for the folder tree utility functions used
 * by the Knowledge Base Browser component.
 * 
 * Coverage targets:
 * - buildFolderTree: Tree construction from flat documents
 * - findFolderByPath: Navigation path resolution
 * - getBreadcrumbs: Breadcrumb trail generation
 * - searchTree: Search functionality
 * - getDocumentIdsInFolder: Bulk operations support
 * - Type guards: isFolderNode, isDocumentNode
 */

import { describe, it, expect } from 'vitest';
import {
    buildFolderTree,
    findFolderByPath,
    getBreadcrumbs,
    searchTree,
    getDocumentIdsInFolder,
    getAllDocumentsInFolder,
    isFolderNode,
    isDocumentNode,
    type FolderNode,
    type DocumentNode,
    type TreeNode,
} from '@/lib/folderTree';
import type { Document } from '@/types';

// =============================================================================
// TEST DATA FACTORIES
// =============================================================================

function createDocument(overrides: Partial<Document> = {}): Document {
    return {
        id: `doc-${Math.random().toString(36).substr(2, 9)}`,
        name: 'test-document.pdf',
        source: 'file_upload',
        sourceType: 'file_upload',
        status: 'indexed',
        addedAt: '2024-01-15T10:00:00Z',
        size: 1024,
        ...overrides,
    };
}

function createDocuments(count: number, overrides: Partial<Document> = {}): Document[] {
    return Array.from({ length: count }, (_, i) =>
        createDocument({
            id: `doc-${i}`,
            name: `document-${i}.pdf`,
            ...overrides,
        })
    );
}

// =============================================================================
// TYPE GUARDS TESTS
// =============================================================================

describe('Type Guards', () => {
    describe('isFolderNode', () => {
        it('should return true for folder nodes', () => {
            const folder: FolderNode = {
                id: 'folder-1',
                name: 'Test Folder',
                path: '/test',
                type: 'folder',
                children: [],
                documentCount: 0,
            };
            expect(isFolderNode(folder)).toBe(true);
        });

        it('should return false for document nodes', () => {
            const doc: DocumentNode = {
                id: 'doc-1',
                name: 'test.pdf',
                path: '/test.pdf',
                type: 'file',
                document: createDocument(),
            };
            expect(isFolderNode(doc)).toBe(false);
        });
    });

    describe('isDocumentNode', () => {
        it('should return true for document nodes', () => {
            const doc: DocumentNode = {
                id: 'doc-1',
                name: 'test.pdf',
                path: '/test.pdf',
                type: 'file',
                document: createDocument(),
            };
            expect(isDocumentNode(doc)).toBe(true);
        });

        it('should return false for folder nodes', () => {
            const folder: FolderNode = {
                id: 'folder-1',
                name: 'Test Folder',
                path: '/test',
                type: 'folder',
                children: [],
                documentCount: 0,
            };
            expect(isDocumentNode(folder)).toBe(false);
        });
    });
});

// =============================================================================
// buildFolderTree TESTS
// =============================================================================

describe('buildFolderTree', () => {
    describe('Empty State', () => {
        it('should create root node with empty children for no documents', () => {
            const tree = buildFolderTree([]);

            expect(tree.id).toBe('root');
            expect(tree.name).toBe('All Documents');
            expect(tree.path).toBe('/');
            expect(tree.type).toBe('folder');
            expect(tree.children).toHaveLength(0);
            expect(tree.documentCount).toBe(0);
        });
    });

    describe('Source Grouping', () => {
        it('should group documents by source type', () => {
            const documents = [
                createDocument({ sourceType: 'file_upload', name: 'upload1.pdf' }),
                createDocument({ sourceType: 'google_drive', name: 'drive1.pdf' }),
                createDocument({ sourceType: 'notion', name: 'notion1.pdf' }),
            ];

            const tree = buildFolderTree(documents);

            expect(tree.children).toHaveLength(3);
            expect(tree.documentCount).toBe(3);

            const sourceNames = tree.children.map(c => (c as FolderNode).sourceType);
            expect(sourceNames).toContain('file_upload');
            expect(sourceNames).toContain('google_drive');
            expect(sourceNames).toContain('notion');
        });

        it('should use file_upload as default source type', () => {
            const doc = createDocument();
            // @ts-expect-error - testing undefined sourceType
            doc.sourceType = undefined;

            const tree = buildFolderTree([doc]);

            expect(tree.children).toHaveLength(1);
            expect((tree.children[0] as FolderNode).sourceType).toBe('file_upload');
        });

        it('should format source names correctly', () => {
            const documents = [
                createDocument({ sourceType: 'google_drive' }),
                createDocument({ sourceType: 'file_upload' }),
                createDocument({ sourceType: 'notion' }),
                createDocument({ sourceType: 'web' }),
                createDocument({ sourceType: 'onedrive' }),
                createDocument({ sourceType: 'sharepoint' }),
                createDocument({ sourceType: 'dropbox' }),
            ];

            const tree = buildFolderTree(documents);

            const names = tree.children.map(c => c.name);
            expect(names).toContain('🔷 Google Drive');
            expect(names).toContain('📁 Uploaded Files');
            expect(names).toContain('📝 Notion');
            expect(names).toContain('🌐 Web Pages');
            expect(names).toContain('☁️ OneDrive');
            expect(names).toContain('📊 SharePoint');
            expect(names).toContain('📦 Dropbox');
        });

        it('should format unknown source types with title case', () => {
            const documents = [
                // @ts-expect-error - testing unknown source type
                createDocument({ sourceType: 'custom_unknown_source' }),
            ];

            const tree = buildFolderTree(documents);

            const sourceFolder = tree.children[0] as FolderNode;
            // Unknown source types should be formatted with title case
            expect(sourceFolder.name).toBe('Custom Unknown Source');
        });

        it('should sort source folders alphabetically', () => {
            const documents = [
                createDocument({ sourceType: 'notion' }),
                createDocument({ sourceType: 'google_drive' }),
                createDocument({ sourceType: 'file_upload' }),
            ];

            const tree = buildFolderTree(documents);
            const names = tree.children.map(c => c.name);

            // Should be sorted alphabetically
            expect(names).toEqual([...names].sort((a, b) => a.localeCompare(b)));
        });
    });

    describe('Path-based Folder Hierarchy', () => {
        it('should create nested folders from document paths', () => {
            const documents = [
                createDocument({
                    sourceType: 'file_upload',
                    name: 'report.pdf',
                    path: '/Projects/Q4/Reports/report.pdf',
                }),
            ];

            const tree = buildFolderTree(documents);
            const sourceFolder = tree.children[0] as FolderNode;

            // Source folder should have Projects folder
            expect(sourceFolder.children).toHaveLength(1);
            expect(sourceFolder.children[0].name).toBe('Projects');

            // Projects should have Q4
            const projectsFolder = sourceFolder.children[0] as FolderNode;
            expect(projectsFolder.children).toHaveLength(1);
            expect(projectsFolder.children[0].name).toBe('Q4');

            // Q4 should have Reports
            const q4Folder = projectsFolder.children[0] as FolderNode;
            expect(q4Folder.children).toHaveLength(1);
            expect(q4Folder.children[0].name).toBe('Reports');

            // Reports should have the document
            const reportsFolder = q4Folder.children[0] as FolderNode;
            expect(reportsFolder.children).toHaveLength(1);
            expect(isDocumentNode(reportsFolder.children[0])).toBe(true);
            expect(reportsFolder.children[0].name).toBe('report.pdf');
        });

        it('should place documents without path directly in source folder', () => {
            const documents = [
                createDocument({
                    sourceType: 'file_upload',
                    name: 'standalone.pdf',
                    path: undefined,
                }),
            ];

            const tree = buildFolderTree(documents);
            const sourceFolder = tree.children[0] as FolderNode;

            expect(sourceFolder.children).toHaveLength(1);
            expect(isDocumentNode(sourceFolder.children[0])).toBe(true);
            expect(sourceFolder.children[0].name).toBe('standalone.pdf');
        });

        it('should place documents with simple filename path directly in source folder', () => {
            const documents = [
                createDocument({
                    sourceType: 'file_upload',
                    name: 'simple.pdf',
                    path: 'simple.pdf',
                }),
            ];

            const tree = buildFolderTree(documents);
            const sourceFolder = tree.children[0] as FolderNode;

            expect(sourceFolder.children).toHaveLength(1);
            expect(isDocumentNode(sourceFolder.children[0])).toBe(true);
        });

        it('should use document name when path segment is empty', () => {
            const documents = [
                createDocument({
                    sourceType: 'file_upload',
                    name: 'fallback-name.pdf',
                    path: '/folder/', // Path ends with slash, no filename segment
                }),
            ];

            const tree = buildFolderTree(documents);
            const sourceFolder = tree.children[0] as FolderNode;
            
            // Find the document node (might be in a folder)
            let docNode: DocumentNode | null = null;
            function findDoc(node: TreeNode): void {
                if (isDocumentNode(node)) {
                    docNode = node;
                } else if (isFolderNode(node)) {
                    node.children.forEach(findDoc);
                }
            }
            sourceFolder.children.forEach(findDoc);
            
            // The document should use the doc.name as fallback
            expect(docNode).not.toBeNull();
            expect(docNode!.name).toBe('fallback-name.pdf');
        });

        it('should use document name when last path segment is empty string', () => {
            // Create document with path that will have empty last segment after split
            const documents = [
                createDocument({
                    sourceType: 'file_upload',
                    name: 'my-document.pdf',
                    path: '/', // Just root slash
                }),
            ];

            const tree = buildFolderTree(documents);
            const sourceFolder = tree.children[0] as FolderNode;
            
            // Document should be placed directly in source folder with doc.name
            const docNode = sourceFolder.children[0] as DocumentNode;
            expect(isDocumentNode(docNode)).toBe(true);
            expect(docNode.name).toBe('my-document.pdf');
        });

        it('should handle path with only folder segments (no filename)', () => {
            // Path has segments but last one would be empty after extracting
            const documents = [
                createDocument({
                    sourceType: 'file_upload',
                    name: 'fallback.txt',
                    path: '/folder1/folder2/', // Trailing slash means no filename
                }),
            ];

            const tree = buildFolderTree(documents);
            const allDocs = getAllDocumentsInFolder(tree);
            
            // Should use doc.name as the document name since last segment is empty
            expect(allDocs[0].name).toBe('fallback.txt');
        });

        it('should use document name when segments array would produce empty last element', () => {
            // Create multiple edge case paths
            const documents = [
                createDocument({
                    sourceType: 'file_upload',
                    name: 'edge-case-1.pdf',
                    path: '', // Empty path
                }),
                createDocument({
                    sourceType: 'file_upload', 
                    name: 'edge-case-2.pdf',
                    path: '/a/b/c/', // Trailing slash
                }),
            ];

            const tree = buildFolderTree(documents);
            const allDocs = getAllDocumentsInFolder(tree);
            
            // Both should use doc.name as fallback
            const names = allDocs.map(d => d.name);
            expect(names).toContain('edge-case-1.pdf');
            expect(names).toContain('edge-case-2.pdf');
        });

        it('should handle multiple documents in same folder', () => {
            const documents = [
                createDocument({
                    sourceType: 'file_upload',
                    name: 'doc1.pdf',
                    path: '/Reports/doc1.pdf',
                }),
                createDocument({
                    sourceType: 'file_upload',
                    name: 'doc2.pdf',
                    path: '/Reports/doc2.pdf',
                }),
                createDocument({
                    sourceType: 'file_upload',
                    name: 'doc3.pdf',
                    path: '/Reports/doc3.pdf',
                }),
            ];

            const tree = buildFolderTree(documents);
            const sourceFolder = tree.children[0] as FolderNode;
            const reportsFolder = sourceFolder.children[0] as FolderNode;

            expect(reportsFolder.name).toBe('Reports');
            expect(reportsFolder.children).toHaveLength(3);
            expect(reportsFolder.documentCount).toBe(3);
        });

        it('should handle documents in different nested paths', () => {
            const documents = [
                createDocument({
                    sourceType: 'file_upload',
                    path: '/A/B/C/doc1.pdf',
                }),
                createDocument({
                    sourceType: 'file_upload',
                    path: '/A/B/D/doc2.pdf',
                }),
                createDocument({
                    sourceType: 'file_upload',
                    path: '/A/E/doc3.pdf',
                }),
            ];

            const tree = buildFolderTree(documents);
            const sourceFolder = tree.children[0] as FolderNode;

            // A should exist
            expect(sourceFolder.children).toHaveLength(1);
            const folderA = sourceFolder.children[0] as FolderNode;
            expect(folderA.name).toBe('A');

            // A should have B and E
            expect(folderA.children).toHaveLength(2);
            expect(folderA.documentCount).toBe(3);
        });
    });

    describe('Document Count Calculation', () => {
        it('should calculate correct document counts for nested folders', () => {
            const documents = [
                createDocument({ sourceType: 'file_upload', path: '/A/doc1.pdf' }),
                createDocument({ sourceType: 'file_upload', path: '/A/B/doc2.pdf' }),
                createDocument({ sourceType: 'file_upload', path: '/A/B/doc3.pdf' }),
                createDocument({ sourceType: 'file_upload', path: '/A/B/C/doc4.pdf' }),
            ];

            const tree = buildFolderTree(documents);
            const sourceFolder = tree.children[0] as FolderNode;
            const folderA = sourceFolder.children[0] as FolderNode;
            const folderB = folderA.children.find(c => c.name === 'B') as FolderNode;
            const folderC = folderB.children.find(c => c.name === 'C') as FolderNode;

            expect(tree.documentCount).toBe(4);
            expect(sourceFolder.documentCount).toBe(4);
            expect(folderA.documentCount).toBe(4);
            expect(folderB.documentCount).toBe(3);
            expect(folderC.documentCount).toBe(1);
        });
    });

    describe('Sorting', () => {
        it('should sort folders before files', () => {
            const documents = [
                createDocument({
                    sourceType: 'file_upload',
                    name: 'zebra.pdf',
                    path: '/zebra.pdf',
                }),
                createDocument({
                    sourceType: 'file_upload',
                    name: 'in-folder.pdf',
                    path: '/apple/in-folder.pdf',
                }),
            ];

            const tree = buildFolderTree(documents);
            const sourceFolder = tree.children[0] as FolderNode;

            // First should be the 'apple' folder
            expect(isFolderNode(sourceFolder.children[0])).toBe(true);
            expect(sourceFolder.children[0].name).toBe('apple');

            // Second should be the file
            expect(isDocumentNode(sourceFolder.children[1])).toBe(true);
            expect(sourceFolder.children[1].name).toBe('zebra.pdf');
        });

        it('should sort folders alphabetically (case-insensitive)', () => {
            const documents = [
                createDocument({ sourceType: 'file_upload', path: '/Zebra/doc.pdf' }),
                createDocument({ sourceType: 'file_upload', path: '/apple/doc.pdf' }),
                createDocument({ sourceType: 'file_upload', path: '/Banana/doc.pdf' }),
            ];

            const tree = buildFolderTree(documents);
            const sourceFolder = tree.children[0] as FolderNode;

            const folderNames = sourceFolder.children
                .filter(isFolderNode)
                .map(f => f.name);

            expect(folderNames).toEqual(['apple', 'Banana', 'Zebra']);
        });

        it('should sort files alphabetically (case-insensitive)', () => {
            const documents = [
                createDocument({ sourceType: 'file_upload', name: 'Zebra.pdf', path: 'Zebra.pdf' }),
                createDocument({ sourceType: 'file_upload', name: 'apple.pdf', path: 'apple.pdf' }),
                createDocument({ sourceType: 'file_upload', name: 'Banana.pdf', path: 'Banana.pdf' }),
            ];

            const tree = buildFolderTree(documents);
            const sourceFolder = tree.children[0] as FolderNode;

            const fileNames = sourceFolder.children
                .filter(isDocumentNode)
                .map(f => f.name);

            expect(fileNames).toEqual(['apple.pdf', 'Banana.pdf', 'Zebra.pdf']);
        });
    });

    describe('Edge Cases', () => {
        it('should handle paths with backslashes (Windows-style) by treating as filename', () => {
            // Note: Backend should normalize paths before sending to frontend
            // Backslash paths are treated as single filenames since split is on "/"
            const documents = [
                createDocument({
                    sourceType: 'file_upload',
                    name: 'doc.pdf',
                    path: '\\Projects\\Reports\\doc.pdf',
                }),
            ];

            const tree = buildFolderTree(documents);
            const sourceFolder = tree.children[0] as FolderNode;

            // Backslash path is treated as a single segment (filename), placed directly in source
            expect(sourceFolder.children).toHaveLength(1);
            expect(isDocumentNode(sourceFolder.children[0])).toBe(true);
        });

        it('should handle empty path segments', () => {
            const documents = [
                createDocument({
                    sourceType: 'file_upload',
                    path: '//Projects///Reports//doc.pdf',
                }),
            ];

            const tree = buildFolderTree(documents);
            const sourceFolder = tree.children[0] as FolderNode;

            // Should filter out empty segments
            expect(sourceFolder.children[0].name).toBe('Projects');
        });

        it('should handle large number of documents', () => {
            const documents = createDocuments(1000, {
                sourceType: 'file_upload',
            });

            const tree = buildFolderTree(documents);

            expect(tree.documentCount).toBe(1000);
        });

        it('should handle deeply nested paths', () => {
            const deepPath = '/a/b/c/d/e/f/g/h/i/j/doc.pdf';
            const documents = [
                createDocument({
                    sourceType: 'file_upload',
                    path: deepPath,
                }),
            ];

            const tree = buildFolderTree(documents);

            expect(tree.documentCount).toBe(1);
        });

        it('should preserve document data in tree nodes', () => {
            const originalDoc = createDocument({
                id: 'unique-id',
                name: 'important.pdf',
                sourceType: 'file_upload',
                size: 5000,
                errorMessage: 'Some error',
            });

            const tree = buildFolderTree([originalDoc]);
            const sourceFolder = tree.children[0] as FolderNode;
            const docNode = sourceFolder.children[0] as DocumentNode;

            expect(docNode.document.id).toBe('unique-id');
            expect(docNode.document.size).toBe(5000);
            expect(docNode.document.errorMessage).toBe('Some error');
        });
    });
});

// =============================================================================
// findFolderByPath TESTS
// =============================================================================

describe('findFolderByPath', () => {
    const createTestTree = () => {
        const documents = [
            createDocument({ sourceType: 'file_upload', path: '/Projects/Q4/report.pdf' }),
            createDocument({ sourceType: 'file_upload', path: '/Archive/old.pdf' }),
            createDocument({ sourceType: 'google_drive', path: '/Shared/doc.pdf' }),
        ];
        return buildFolderTree(documents);
    };

    it('should find root folder with "/" path', () => {
        const tree = createTestTree();
        const found = findFolderByPath(tree, '/');

        expect(found).not.toBeNull();
        expect(found?.id).toBe('root');
        expect(found?.name).toBe('All Documents');
    });

    it('should find root folder with root path', () => {
        const tree = createTestTree();
        const found = findFolderByPath(tree, tree.path);

        expect(found).not.toBeNull();
        expect(found?.id).toBe('root');
    });

    it('should find source folder', () => {
        const tree = createTestTree();
        const found = findFolderByPath(tree, '/file_upload');

        expect(found).not.toBeNull();
        expect(found?.sourceType).toBe('file_upload');
    });

    it('should find nested folder', () => {
        const tree = createTestTree();
        const found = findFolderByPath(tree, '/file_upload/Projects');

        expect(found).not.toBeNull();
        expect(found?.name).toBe('Projects');
    });

    it('should find deeply nested folder', () => {
        const tree = createTestTree();
        const found = findFolderByPath(tree, '/file_upload/Projects/Q4');

        expect(found).not.toBeNull();
        expect(found?.name).toBe('Q4');
    });

    it('should return null for non-existent path', () => {
        const tree = createTestTree();
        const found = findFolderByPath(tree, '/nonexistent/path');

        expect(found).toBeNull();
    });

    it('should return null for file paths', () => {
        const tree = createTestTree();
        // This path points to a file, not a folder
        const found = findFolderByPath(tree, '/file_upload/Projects/Q4/report.pdf');

        expect(found).toBeNull();
    });

    it('should handle partial path that exists', () => {
        const documents = [
            createDocument({ sourceType: 'file_upload', path: '/A/B/C/doc.pdf' }),
        ];
        const tree = buildFolderTree(documents);

        const folderA = findFolderByPath(tree, '/file_upload/A');
        const folderB = findFolderByPath(tree, '/file_upload/A/B');
        const folderC = findFolderByPath(tree, '/file_upload/A/B/C');

        expect(folderA?.name).toBe('A');
        expect(folderB?.name).toBe('B');
        expect(folderC?.name).toBe('C');
    });
});

// =============================================================================
// getBreadcrumbs TESTS
// =============================================================================

describe('getBreadcrumbs', () => {
    const createTestTree = () => {
        const documents = [
            createDocument({ sourceType: 'file_upload', path: '/Projects/Q4/Reports/report.pdf' }),
        ];
        return buildFolderTree(documents);
    };

    it('should return only root for "/" path', () => {
        const tree = createTestTree();
        const breadcrumbs = getBreadcrumbs(tree, '/');

        expect(breadcrumbs).toHaveLength(1);
        expect(breadcrumbs[0].name).toBe('All Documents');
        expect(breadcrumbs[0].path).toBe('/');
    });

    it('should return full breadcrumb trail for nested path', () => {
        const tree = createTestTree();
        const breadcrumbs = getBreadcrumbs(tree, '/file_upload/Projects/Q4');

        expect(breadcrumbs).toHaveLength(4);
        expect(breadcrumbs[0].name).toBe('All Documents');
        expect(breadcrumbs[1].name).toBe('📁 Uploaded Files');
        expect(breadcrumbs[2].name).toBe('Projects');
        expect(breadcrumbs[3].name).toBe('Q4');
    });

    it('should include id and path for each breadcrumb', () => {
        const tree = createTestTree();
        const breadcrumbs = getBreadcrumbs(tree, '/file_upload/Projects');

        breadcrumbs.forEach(crumb => {
            expect(crumb).toHaveProperty('id');
            expect(crumb).toHaveProperty('name');
            expect(crumb).toHaveProperty('path');
            expect(typeof crumb.id).toBe('string');
            expect(typeof crumb.name).toBe('string');
            expect(typeof crumb.path).toBe('string');
        });
    });

    it('should handle source folder path', () => {
        const tree = createTestTree();
        const breadcrumbs = getBreadcrumbs(tree, '/file_upload');

        expect(breadcrumbs).toHaveLength(2);
        expect(breadcrumbs[1].name).toBe('📁 Uploaded Files');
    });

    it('should handle root path', () => {
        const tree = createTestTree();
        const breadcrumbs = getBreadcrumbs(tree, tree.path);

        expect(breadcrumbs).toHaveLength(1);
        expect(breadcrumbs[0].id).toBe('root');
    });

    it('should handle path matching by name when path does not match exactly', () => {
        // This tests the fallback logic where we match by folder name
        const documents = [
            createDocument({ sourceType: 'file_upload', path: '/MyFolder/doc.pdf' }),
        ];
        const tree = buildFolderTree(documents);
        
        // Try to get breadcrumbs with a slightly different path format
        // The function should still find the folder by name
        const breadcrumbs = getBreadcrumbs(tree, '/file_upload/MyFolder');

        expect(breadcrumbs.length).toBeGreaterThanOrEqual(2);
        const folderNames = breadcrumbs.map(b => b.name);
        expect(folderNames).toContain('MyFolder');
    });

    it('should use fallback name matching when direct path lookup fails', () => {
        // Create a tree with a specific structure
        const documents = [
            createDocument({ sourceType: 'file_upload', path: '/Projects/Reports/doc.pdf' }),
        ];
        const tree = buildFolderTree(documents);
        
        // Manually access a folder and then try breadcrumbs with a non-matching path
        // The fallback should find folders by name
        const sourceFolder = tree.children[0] as FolderNode;
        const projectsFolder = sourceFolder.children[0] as FolderNode;
        
        // Create a path that won't match exactly but should match by folder name
        // This tests the else branch in getBreadcrumbs (lines 346-359)
        const breadcrumbs = getBreadcrumbs(tree, `${sourceFolder.path}/Projects/Reports`);
        
        expect(breadcrumbs.length).toBeGreaterThanOrEqual(3);
        expect(breadcrumbs.some(b => b.name === 'Projects')).toBe(true);
        expect(breadcrumbs.some(b => b.name === 'Reports')).toBe(true);
    });

    it('should handle partial path that does not exist', () => {
        const documents = [
            createDocument({ sourceType: 'file_upload', path: '/A/B/doc.pdf' }),
        ];
        const tree = buildFolderTree(documents);
        
        // Request breadcrumbs for a path where middle segment doesn't exist
        const breadcrumbs = getBreadcrumbs(tree, '/file_upload/A/NonExistent/B');
        
        // Should return partial breadcrumbs up to where it can find folders
        expect(breadcrumbs.length).toBeGreaterThanOrEqual(1);
        expect(breadcrumbs[0].name).toBe('All Documents');
    });
});

// =============================================================================
// searchTree TESTS
// =============================================================================

describe('searchTree', () => {
    const createTestTree = () => {
        const documents = [
            createDocument({ sourceType: 'file_upload', name: 'quarterly-report.pdf', path: '/Reports/quarterly-report.pdf' }),
            createDocument({ sourceType: 'file_upload', name: 'annual-report.pdf', path: '/Reports/annual-report.pdf' }),
            createDocument({ sourceType: 'file_upload', name: 'meeting-notes.docx', path: '/Notes/meeting-notes.docx' }),
            createDocument({ sourceType: 'google_drive', name: 'drive-file.pdf', path: '/Shared/drive-file.pdf' }),
        ];
        return buildFolderTree(documents);
    };

    it('should return all children for empty query', () => {
        const tree = createTestTree();
        const results = searchTree(tree, '');

        expect(results).toEqual(tree.children);
    });

    it('should return all children for whitespace-only query', () => {
        const tree = createTestTree();
        const results = searchTree(tree, '   ');

        expect(results).toEqual(tree.children);
    });

    it('should find documents by name', () => {
        const tree = createTestTree();
        const results = searchTree(tree, 'quarterly');

        const docResults = results.filter(isDocumentNode);
        expect(docResults.length).toBeGreaterThan(0);
        expect(docResults.some(d => d.name.includes('quarterly'))).toBe(true);
    });

    it('should find folders by name', () => {
        const tree = createTestTree();
        const results = searchTree(tree, 'Reports');

        const folderResults = results.filter(isFolderNode);
        expect(folderResults.some(f => f.name === 'Reports')).toBe(true);
    });

    it('should be case-insensitive', () => {
        const tree = createTestTree();
        const lowerResults = searchTree(tree, 'report');
        const upperResults = searchTree(tree, 'REPORT');
        const mixedResults = searchTree(tree, 'RePoRt');

        // All should find the same items
        expect(lowerResults.length).toBe(upperResults.length);
        expect(lowerResults.length).toBe(mixedResults.length);
    });

    it('should search document paths', () => {
        const tree = createTestTree();
        const results = searchTree(tree, 'Shared');

        // Should find the drive-file.pdf which has /Shared/ in its path
        const docs = results.filter(isDocumentNode);
        expect(docs.some(d => d.document.path?.includes('Shared'))).toBe(true);
    });

    it('should search document source types', () => {
        const tree = createTestTree();
        const results = searchTree(tree, 'google_drive');

        const docs = results.filter(isDocumentNode);
        expect(docs.some(d => d.document.sourceType === 'google_drive')).toBe(true);
    });

    it('should return empty array when no matches', () => {
        const tree = createTestTree();
        const results = searchTree(tree, 'xyznonexistent123');

        expect(results).toHaveLength(0);
    });
});

// =============================================================================
// getAllDocumentsInFolder TESTS
// =============================================================================

describe('getAllDocumentsInFolder', () => {
    it('should return all documents from a folder', () => {
        const documents = [
            createDocument({ id: 'doc-1', sourceType: 'file_upload', path: '/folder1/doc1.pdf' }),
            createDocument({ id: 'doc-2', sourceType: 'file_upload', path: '/folder1/doc2.pdf' }),
            createDocument({ id: 'doc-3', sourceType: 'file_upload', path: '/folder2/doc3.pdf' }),
        ];

        const tree = buildFolderTree(documents);
        const sourceFolder = tree.children[0] as FolderNode;
        const folder1 = sourceFolder.children.find(c => c.name === 'folder1') as FolderNode;

        const docsInFolder1 = getAllDocumentsInFolder(folder1);

        expect(docsInFolder1).toHaveLength(2);
        expect(docsInFolder1.map(d => d.id)).toContain('doc-1');
        expect(docsInFolder1.map(d => d.id)).toContain('doc-2');
    });

    it('should include documents from subfolders', () => {
        const documents = [
            createDocument({ id: 'doc-1', sourceType: 'file_upload', path: '/A/doc1.pdf' }),
            createDocument({ id: 'doc-2', sourceType: 'file_upload', path: '/A/B/doc2.pdf' }),
            createDocument({ id: 'doc-3', sourceType: 'file_upload', path: '/A/B/C/doc3.pdf' }),
        ];

        const tree = buildFolderTree(documents);
        const sourceFolder = tree.children[0] as FolderNode;
        const folderA = sourceFolder.children[0] as FolderNode;

        const docsInA = getAllDocumentsInFolder(folderA);

        expect(docsInA).toHaveLength(3);
    });

    it('should return empty array for empty folder', () => {
        const folder: FolderNode = {
            id: 'empty',
            name: 'Empty',
            path: '/empty',
            type: 'folder',
            children: [],
            documentCount: 0,
        };

        const docs = getAllDocumentsInFolder(folder);
        expect(docs).toHaveLength(0);
    });

    it('should return all documents from root', () => {
        const documents = createDocuments(10, { sourceType: 'file_upload' });
        const tree = buildFolderTree(documents);

        const allDocs = getAllDocumentsInFolder(tree);

        expect(allDocs).toHaveLength(10);
    });
});

// =============================================================================
// getDocumentIdsInFolder TESTS
// =============================================================================

describe('getDocumentIdsInFolder', () => {
    it('should return document IDs from folder', () => {
        const documents = [
            createDocument({ id: 'id-a', sourceType: 'file_upload', path: '/folder/a.pdf' }),
            createDocument({ id: 'id-b', sourceType: 'file_upload', path: '/folder/b.pdf' }),
        ];

        const tree = buildFolderTree(documents);
        const sourceFolder = tree.children[0] as FolderNode;
        const folder = sourceFolder.children[0] as FolderNode;

        const ids = getDocumentIdsInFolder(folder);

        expect(ids).toContain('id-a');
        expect(ids).toContain('id-b');
        expect(ids).toHaveLength(2);
    });

    it('should return IDs from nested folders', () => {
        const documents = [
            createDocument({ id: 'id-1', sourceType: 'file_upload', path: '/A/B/doc.pdf' }),
            createDocument({ id: 'id-2', sourceType: 'file_upload', path: '/A/C/doc.pdf' }),
        ];

        const tree = buildFolderTree(documents);
        const sourceFolder = tree.children[0] as FolderNode;
        const folderA = sourceFolder.children[0] as FolderNode;

        const ids = getDocumentIdsInFolder(folderA);

        expect(ids).toContain('id-1');
        expect(ids).toContain('id-2');
    });

    it('should return empty array for empty folder', () => {
        const folder: FolderNode = {
            id: 'empty',
            name: 'Empty',
            path: '/empty',
            type: 'folder',
            children: [],
            documentCount: 0,
        };

        const ids = getDocumentIdsInFolder(folder);
        expect(ids).toHaveLength(0);
    });
});

// =============================================================================
// INTEGRATION TESTS
// =============================================================================

describe('Integration Tests', () => {
    it('should handle real-world document structure', () => {
        const documents: Document[] = [
            // File uploads with various paths
            createDocument({ id: '1', sourceType: 'file_upload', name: 'readme.md', path: 'readme.md' }),
            createDocument({ id: '2', sourceType: 'file_upload', name: 'report-q1.pdf', path: '/Reports/2024/Q1/report-q1.pdf' }),
            createDocument({ id: '3', sourceType: 'file_upload', name: 'report-q2.pdf', path: '/Reports/2024/Q2/report-q2.pdf' }),
            createDocument({ id: '4', sourceType: 'file_upload', name: 'contract.pdf', path: '/Legal/Contracts/contract.pdf' }),

            // Google Drive
            createDocument({ id: '5', sourceType: 'google_drive', name: 'shared-doc.gdoc', path: '/Shared/Team/shared-doc.gdoc' }),
            createDocument({ id: '6', sourceType: 'google_drive', name: 'personal.gdoc', path: '/My Drive/personal.gdoc' }),

            // Notion pages
            createDocument({ id: '7', sourceType: 'notion', name: 'Product Roadmap', path: '/Workspace/Product/Product Roadmap' }),
            createDocument({ id: '8', sourceType: 'notion', name: 'Meeting Notes', path: '/Workspace/Meetings/Meeting Notes' }),

            // Web pages
            createDocument({ id: '9', sourceType: 'web', name: 'Documentation', path: 'https://docs.example.com' }),
        ];

        const tree = buildFolderTree(documents);

        // Verify total count
        expect(tree.documentCount).toBe(9);

        // Verify source folders exist
        expect(tree.children.length).toBe(4); // file_upload, google_drive, notion, web

        // Navigate to a specific folder
        const reportsQ1 = findFolderByPath(tree, '/file_upload/Reports/2024/Q1');
        expect(reportsQ1).not.toBeNull();
        expect(reportsQ1?.documentCount).toBe(1);

        // Get breadcrumbs
        const breadcrumbs = getBreadcrumbs(tree, '/file_upload/Reports/2024/Q1');
        expect(breadcrumbs.map(b => b.name)).toEqual([
            'All Documents',
            '📁 Uploaded Files',
            'Reports',
            '2024',
            'Q1'
        ]);

        // Search
        const searchResults = searchTree(tree, 'report');
        const reportDocs = searchResults.filter(isDocumentNode);
        expect(reportDocs.length).toBeGreaterThanOrEqual(2);

        // Get IDs for bulk delete
        const fileUploadFolder = tree.children.find(c => (c as FolderNode).sourceType === 'file_upload') as FolderNode;
        const allFileUploadIds = getDocumentIdsInFolder(fileUploadFolder);
        expect(allFileUploadIds).toHaveLength(4);
    });

    it('should maintain consistency after tree operations', () => {
        const documents = createDocuments(50, { sourceType: 'file_upload' });

        const tree = buildFolderTree(documents);

        // Count should match
        expect(tree.documentCount).toBe(50);

        // All documents should be retrievable
        const allDocs = getAllDocumentsInFolder(tree);
        expect(allDocs).toHaveLength(50);

        // All IDs should be unique
        const allIds = getDocumentIdsInFolder(tree);
        const uniqueIds = new Set(allIds);
        expect(uniqueIds.size).toBe(50);
    });
});
