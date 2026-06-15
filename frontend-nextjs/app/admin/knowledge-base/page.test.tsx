import { fireEvent, render, screen } from '@testing-library/react';

import { ApprovedKnowledgeCardsPanel } from './ApprovedKnowledgeCardsPanel';
import { PackagesTab } from './KnowledgePackagesPanel';

describe('ApprovedKnowledgeCardsPanel', () => {
  it('renders approved knowledge card governance summary and cards', () => {
    render(
      <ApprovedKnowledgeCardsPanel
        loading={false}
        cards={[
          {
            card_id: 'KC-TEA-QUEUE-PICKUP-FLOW-001',
            title: '茶饮门店点单等候取餐三线解耦机制',
            status: 'approved',
            evidence_level: 'supporting_evidence',
            evidence_strength: 'B',
            knowledge_status: 'processed_insight',
            source_role: 'operation_method',
            package_ids: ['kp.tea_drink_store', 'kp.customer_flow'],
            ontology_dimension_ids: ['E2_body_movement', 'E6_operation_system'],
            allowed_use: ['operation_flow_strategy'],
            not_allowed_use: ['business_performance_claim'],
            output_usage: ['DesignBrief_2_0'],
            task_brief_chapter: ['operation_flow'],
            v33_complete: true,
            missing_v33_fields: [],
          },
        ]}
        summary={{
          approved_card_count: 4,
          v33_complete_count: 4,
          missing_v33_field_count: 0,
          package_with_cards_count: 7,
        }}
        onReload={() => undefined}
      />
    );

    expect(screen.getByText('Approved Knowledge Cards')).toBeInTheDocument();
    expect(screen.getByText('茶饮门店点单等候取餐三线解耦机制')).toBeInTheDocument();
    expect(screen.getByText('KC-TEA-QUEUE-PICKUP-FLOW-001')).toBeInTheDocument();
    expect(screen.getAllByText('v3.3 完整').length).toBeGreaterThan(0);
    expect(screen.getByText('kp.tea_drink_store')).toBeInTheDocument();
    expect(screen.getByText('operation_flow_strategy')).toBeInTheDocument();
    expect(screen.getByText('business_performance_claim')).toBeInTheDocument();
  });
});

describe('PackagesTab', () => {
  it('renders knowledge package governance, activation references, and card coverage', () => {
    const onOpenPackage = jest.fn();

    render(
      <PackagesTab
        packages={[
          {
            package_id: 'kp.tea_drink_store',
            title: 'Tea drink store operations',
            project_types: ['commercial_dining'],
            search_tags: ['tea_bar', 'takeaway_priority'],
            document_types: ['method_card'],
            status: 'active',
            document_count: 2,
            approved_card_count: 3,
            approved_card_ids: [
              'KC-TEA-QUEUE-PICKUP-FLOW-001',
              'KC-TEA-ORDER-ZONE-002',
              'KC-TEA-BACKBAR-003',
            ],
            activation_pack_ids: ['tea_drink_store_pack'],
            activation_pack_ref_count: 1,
            coverage_status: 'ready',
          },
          {
            package_id: 'kp.coffee_shop',
            title: 'Coffee shop baseline',
            project_types: ['commercial_dining'],
            search_tags: ['coffee_shop'],
            document_types: [],
            status: 'active',
            document_count: 0,
            approved_card_count: 0,
            activation_pack_ids: ['coffee_shop_pack'],
            activation_pack_ref_count: 1,
            coverage_status: 'referenced_no_cards',
          },
        ]}
        loading={false}
        selectedPackageId=""
        setSelectedPackageId={() => undefined}
        packageDocuments={[]}
        loadingPackageDocuments={false}
        documentTypes={[]}
        selectedDocumentType=""
        showUnboundDocs={false}
        countsAvailable={true}
        packageCountError=""
        unboundDocumentCount={5}
        importingSamples={false}
        onOpenPackage={onOpenPackage}
        onOpenUnbound={() => undefined}
        onClosePackage={() => undefined}
        onSelectDocumentType={() => undefined}
        onImportSamples={() => undefined}
        onReload={() => undefined}
      />
    );

    expect(screen.getByText('kp.tea_drink_store')).toBeInTheDocument();
    expect(screen.getByText('kp.coffee_shop')).toBeInTheDocument();
    expect(screen.getByText('Tea drink store operations')).toBeInTheDocument();
    expect(screen.getByText((text) => text.includes('tea_drink_store_pack'))).toBeInTheDocument();
    expect(screen.getByText((text) => text.includes('coffee_shop_pack'))).toBeInTheDocument();
    expect(screen.getByText('tea_bar')).toBeInTheDocument();
    expect(screen.getByText('takeaway_priority')).toBeInTheDocument();
    expect(screen.getByText((text) => text.includes('已审核卡') && text.includes('3'))).toBeInTheDocument();

    fireEvent.click(screen.getByText('kp.tea_drink_store'));
    expect(onOpenPackage).toHaveBeenCalledWith('kp.tea_drink_store');
  });
});
