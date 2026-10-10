// Run from the read-only neomega-blocks module; see docs/waterlogged-candidates.md.
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"neomega_blocks/description"
	"neomega_blocks/preset"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

type Block struct {
	Name   string         `json:"name"`
	States map[string]any `json:"states"`
}

type NativeState struct {
	Name  string `json:"name"`
	Type  string `json:"type"`
	Value any    `json:"value"`
}

type NativeBlock struct {
	Name      string        `json:"name"`
	Data      int           `json:"data"`
	NetworkID uint32        `json:"network_id"`
	States    []NativeState `json:"states"`
}

type NativeKey struct {
	Name string
	Hash uint32
}

type Capability struct {
	Name             string `json:"name"`
	Hash             uint32 `json:"blockStateHash"`
	CanContainLiquid *bool  `json:"canContainLiquid"`
}

type JavaMappingEvidence struct {
	Bedrock string `json:"bedrock"`
	Java    string `json:"java"`
}

type Evidence struct {
	UIBI                    uint32 `json:"uibi"`
	Waterlogged             bool   `json:"waterlogged"`
	Universal               *Block `json:"universal"`
	Java                    Block  `json:"java"`
	Bedrock                 Block  `json:"bedrock"`
	JavaReverseExactUIBI    bool   `json:"java_reverse_exact_uibi"`
	BedrockReverseExactUIBI bool   `json:"bedrock_reverse_exact_uibi"`
}

type Row struct {
	Name                             string                `json:"name"`
	Status                           string                `json:"status"`
	Candidate                        bool                  `json:"candidate"`
	NativeStateCount                 int                   `json:"native_state_count"`
	NativeExample                    *NativeBlock          `json:"native_example,omitempty"`
	MappedUIBICount                  int                   `json:"mapped_uibi_count"`
	JavaOutputCount                  int                   `json:"java_output_count"`
	WaterloggedTrueCount             int                   `json:"waterlogged_true_count"`
	WaterloggedFalseCount            int                   `json:"waterlogged_false_count"`
	JavaNames                        []string              `json:"java_names"`
	Evidence                         []Evidence            `json:"evidence"`
	JavaMappingEvidence              []JavaMappingEvidence `json:"java_mapping_evidence"`
	JavaMappingWaterloggedTrueCount  int                   `json:"java_mapping_waterlogged_true_count"`
	JavaMappingWaterloggedFalseCount int                   `json:"java_mapping_waterlogged_false_count"`
	NativeLiquidAux                  []int                 `json:"native_liquid_aux"`
	NativeCapabilityMatchedCount     int                   `json:"native_capability_matched_count"`
	NativeCapabilityRejectedCount    int                   `json:"native_capability_rejected_count"`
	javaNames                        map[string]bool
	wetEvidence                      []Evidence
	dryEvidence                      []Evidence
}

type SourceFile struct {
	Path   string `json:"path"`
	SHA256 string `json:"sha256"`
}

func describe(block *description.MiddleBlock) Block {
	states := block.GoMapProps()
	if states == nil {
		states = map[string]any{}
	}
	return Block{block.BaseName().LongName(), states}
}

func waterlogged(value any) (bool, bool) {
	switch value := value.(type) {
	case bool:
		return value, true
	case string:
		if value == "true" || value == "false" {
			return value == "true", true
		}
	case byte:
		if value <= 1 {
			return value == 1, true
		}
	case int32:
		if value == 0 || value == 1 {
			return value == 1, true
		}
	}
	return false, false
}

func hashFile(path string) (string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	hash := sha256.Sum256(data)
	return hex.EncodeToString(hash[:]), nil
}

func fail(err error) {
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func sourceMetadata(path string) map[string]any {
	metadata := map[string]any{"file": filepath.Base(path)}
	if revision, err := exec.Command("git", "-C", filepath.Dir(path), "rev-parse", "HEAD").Output(); err == nil {
		metadata["git_revision"] = strings.TrimSpace(string(revision))
	}
	if status, err := exec.Command("git", "-C", filepath.Dir(path), "status", "--porcelain").Output(); err == nil {
		metadata["git_dirty"] = len(status) != 0
	}
	return metadata
}

func main() {
	nativePath := flag.String("native", "", "NEMC dump JSON to compare")
	outputPath := flag.String("output", "", "candidate JSON output")
	capabilityPath := flag.String("bedrock-capabilities", "", "optional Bedrock block_states.json containing canContainLiquid")
	javaMappingPath := flag.String("java-mappings", "", "optional Bedrock-to-Java blockstate_mappings.json")
	flag.Parse()
	if *nativePath == "" || *outputPath == "" {
		flag.Usage()
		os.Exit(2)
	}
	sourceRoot, err := os.Getwd()
	fail(err)
	module, err := os.ReadFile(filepath.Join(sourceRoot, "go.mod"))
	fail(err)
	if !strings.Contains(string(module), "module neomega_blocks") {
		fail(fmt.Errorf("run from the neomega-blocks source module"))
	}
	inputs := []string{"preset/preset", "word_bag/words", "preset/gen/main.go", "data/build_unis/source_gen.py", "data/build_unis/target_gen.py", "data/build_unis/versions_iter.py"}
	sources := make([]SourceFile, 0, len(inputs))
	for _, relative := range inputs {
		hash, err := hashFile(filepath.Join(sourceRoot, relative))
		fail(err)
		sources = append(sources, SourceFile{relative, hash})
	}
	nativeHash, err := hashFile(*nativePath)
	fail(err)
	genSource, err := os.ReadFile(filepath.Join(sourceRoot, "preset/gen/main.go"))
	fail(err)
	targets := regexp.MustCompile(`uni_to_(java|bedrock)_([0-9_]+)\.json`).FindAllStringSubmatch(string(genSource), -1)
	declaredTargets := map[string]string{}
	for _, target := range targets {
		declaredTargets[target[1]] = strings.ReplaceAll(target[2], "_", ".")
	}
	revision, err := exec.Command("git", "rev-parse", "HEAD").Output()
	fail(err)
	gitStatus, err := exec.Command("git", "status", "--porcelain").Output()
	fail(err)
	data, err := os.ReadFile(*nativePath)
	fail(err)
	var native struct {
		Blocks []NativeBlock `json:"blocks"`
	}
	fail(json.Unmarshal(data, &native))
	rows := map[string]*Row{}
	nativeByKey := map[NativeKey]NativeBlock{}
	getRow := func(name string) *Row {
		row := rows[name]
		if row == nil {
			row = &Row{Name: name, JavaNames: []string{}, Evidence: []Evidence{}, JavaMappingEvidence: []JavaMappingEvidence{}, NativeLiquidAux: []int{}, javaNames: map[string]bool{}}
			rows[name] = row
		}
		return row
	}
	for _, block := range native.Blocks {
		nativeByKey[NativeKey{block.Name, block.NetworkID}] = block
		row := getRow(block.Name)
		row.NativeStateCount++
		if row.NativeExample == nil || block.Data < row.NativeExample.Data {
			copy := block
			row.NativeExample = &copy
		}
	}
	preset.Load()
	bedrockRecordCount, javaRecordCount := 0, 0
	waterloggedValueTypes := map[string]int{}
	invalidWaterloggedValues := map[string]int{}
	javaPropertyKeys := map[string]int{}
	javaExamples := map[string]Block{}
	reverseProbeHits := map[string]int{}
	// Join exact universal IDs. Fuzzy matches would manufacture unsupported evidence.
	for id, bedrock := range preset.UIBIToBedrock.Iter {
		bedrockRecordCount++
		row := getRow(bedrock.BaseName().LongName())
		row.MappedUIBICount++
		java, found := preset.UIBIToJava.IDToBlock(id)
		if !found || java == nil {
			continue
		}
		row.JavaOutputCount++
		row.javaNames[java.BaseName().LongName()] = true
		props := java.GoMapProps()
		for key := range props {
			javaPropertyKeys[key]++
		}
		if _, found := javaExamples[row.Name]; !found {
			javaExamples[row.Name] = describe(java)
		}
		value, found := props["waterlogged"]
		if !found {
			value, found = props["minecraft:waterlogged"]
		}
		if !found {
			for _, waterValue := range []string{"true", "false"} {
				probeProps := java.GoMapProps()
				if probeProps == nil {
					probeProps = map[string]any{}
				}
				probeProps["waterlogged"] = waterValue
				probe, err := description.ParseBlockState(java.BaseName().LongName(), probeProps, description.DefaultCaster)
				fail(err)
				if _, exact := preset.JavaToUIBI.BlockToID(probe); exact {
					reverseProbeHits[waterValue]++
					if reverseProbeHits[waterValue] <= 2 {
						fmt.Printf("reverse exact hit: %s\n", probe.SNBTString())
					}
				}
			}
			continue
		}
		waterloggedValueTypes[fmt.Sprintf("%T", value)]++
		wet, valid := waterlogged(value)
		if !valid {
			invalidWaterloggedValues[fmt.Sprintf("%T:%v", value, value)]++
			continue
		}
		row.Candidate = true
		if wet {
			row.WaterloggedTrueCount++
		} else {
			row.WaterloggedFalseCount++
		}
		javaReverse, javaFound := preset.JavaToUIBI.BlockToID(java)
		bedrockReverse, bedrockFound := preset.BedrockToUIBI.BlockToID(bedrock)
		evidence := Evidence{UIBI: uint32(id), Waterlogged: wet, Java: describe(java), Bedrock: describe(bedrock), JavaReverseExactUIBI: javaFound && javaReverse == id, BedrockReverseExactUIBI: bedrockFound && bedrockReverse == id}
		if universal, found := preset.UIBIBlocks.IDToBlock(id); found && universal != nil {
			block := describe(universal)
			evidence.Universal = &block
		}
		if wet {
			row.wetEvidence = append(row.wetEvidence, evidence)
		} else {
			row.dryEvidence = append(row.dryEvidence, evidence)
		}
	}
	for range preset.UIBIToJava.Iter {
		javaRecordCount++
	}
	additionalSources := []SourceFile{}
	additionalSourceMetadata := map[string]any{}
	capabilityStats := map[string]int{}
	if *capabilityPath != "" {
		additionalSourceMetadata["bedrock_capabilities"] = sourceMetadata(*capabilityPath)
		hash, err := hashFile(*capabilityPath)
		fail(err)
		additionalSources = append(additionalSources, SourceFile{"PowerNukkitX/src/main/resources/block_states.json", hash})
		data, err := os.ReadFile(*capabilityPath)
		fail(err)
		var records []Capability
		fail(json.Unmarshal(data, &records))
		seen := map[NativeKey]bool{}
		for _, record := range records {
			capabilityStats["source_records"]++
			key := NativeKey{record.Name, record.Hash}
			block, found := nativeByKey[key]
			if !found {
				capabilityStats["unmatched_records"]++
				continue
			}
			if seen[key] {
				capabilityStats["duplicate_records"]++
				continue
			}
			seen[key] = true
			if record.CanContainLiquid == nil {
				capabilityStats["missing_capability_records"]++
				continue
			}
			capabilityStats["native_name_hash_matched_records"]++
			row := getRow(record.Name)
			row.NativeCapabilityMatchedCount++
			if *record.CanContainLiquid {
				row.NativeLiquidAux = append(row.NativeLiquidAux, block.Data)
				capabilityStats["native_liquid_records"]++
			} else {
				row.NativeCapabilityRejectedCount++
			}
		}
	}
	javaMappingStats := map[string]int{}
	if *javaMappingPath != "" {
		additionalSourceMetadata["java_mappings"] = sourceMetadata(*javaMappingPath)
		hash, err := hashFile(*javaMappingPath)
		fail(err)
		additionalSources = append(additionalSources, SourceFile{"ViaBedrock/src/main/resources/assets/viabedrock/data/custom/blockstate_mappings.json", hash})
		data, err := os.ReadFile(*javaMappingPath)
		fail(err)
		var mappings map[string]string
		fail(json.Unmarshal(data, &mappings))
		mappingKeys := make([]string, 0, len(mappings))
		for key := range mappings {
			mappingKeys = append(mappingKeys, key)
		}
		sort.Strings(mappingKeys)
		for _, bedrockString := range mappingKeys {
			javaMappingStats["source_records"]++
			javaString := mappings[bedrockString]
			javaBlock := description.ParsePureStrBlockStr(javaString)
			wet, valid := waterlogged(javaBlock.GoMapProps()["waterlogged"])
			if !valid {
				continue
			}
			javaMappingStats["waterlogged_records"]++
			// Packed source names cannot preserve names absent from neomega's word dictionary.
			bedrockName, _, _ := strings.Cut(bedrockString, "[")
			row := getRow(bedrockName)
			row.Candidate = true
			if wet {
				row.JavaMappingWaterloggedTrueCount++
			} else {
				row.JavaMappingWaterloggedFalseCount++
			}
			row.javaNames[javaBlock.BaseName().LongName()] = true
			if len(row.JavaMappingEvidence) < 2 {
				row.JavaMappingEvidence = append(row.JavaMappingEvidence, JavaMappingEvidence{bedrockString, javaString})
			}
		}
	}
	names := make([]string, 0, len(rows))
	for name := range rows {
		names = append(names, name)
	}
	sort.Strings(names)
	outputRows := make([]*Row, 0, len(rows))
	candidates, nativeCandidates, nativeOnly, mappingOnly := []string{}, []string{}, []string{}, []string{}
	statusCounts := map[string]int{}
	nativeCapabilityCandidates := []string{}
	javaCandidatesRejectedByMatchedStates := []string{}
	for _, name := range names {
		row := rows[name]
		sort.Ints(row.NativeLiquidAux)
		if len(row.NativeLiquidAux) > 0 {
			row.Candidate = true
			nativeCapabilityCandidates = append(nativeCapabilityCandidates, name)
		} else if row.Candidate && row.NativeCapabilityMatchedCount > 0 && row.NativeCapabilityMatchedCount == row.NativeStateCount {
			javaCandidatesRejectedByMatchedStates = append(javaCandidatesRejectedByMatchedStates, name)
		}
		for javaName := range row.javaNames {
			row.JavaNames = append(row.JavaNames, javaName)
		}
		sort.Strings(row.JavaNames)
		sort.Slice(row.wetEvidence, func(i, j int) bool { return row.wetEvidence[i].UIBI < row.wetEvidence[j].UIBI })
		sort.Slice(row.dryEvidence, func(i, j int) bool { return row.dryEvidence[i].UIBI < row.dryEvidence[j].UIBI })
		for _, set := range [][]Evidence{row.wetEvidence, row.dryEvidence} {
			for i, evidence := range set {
				if i == 2 {
					break
				}
				row.Evidence = append(row.Evidence, evidence)
			}
		}
		if row.Candidate {
			row.Status = "java_waterlogged_candidate_unverified"
			if len(row.NativeLiquidAux) > 0 {
				row.Status = "bedrock_can_contain_liquid_candidate_unverified"
			}
			candidates = append(candidates, name)
			if row.NativeStateCount > 0 {
				nativeCandidates = append(nativeCandidates, name)
			}
		} else if row.MappedUIBICount == 0 {
			row.Status = "native_only_no_mapping_evidence"
		} else if row.JavaOutputCount == 0 {
			row.Status = "mapping_without_java_output"
		} else {
			row.Status = "no_java_waterlogged_evidence"
		}
		if row.MappedUIBICount == 0 && row.NativeStateCount > 0 {
			nativeOnly = append(nativeOnly, name)
		}
		if row.NativeStateCount == 0 {
			mappingOnly = append(mappingOnly, name)
		}
		statusCounts[row.Status]++
		outputRows = append(outputRows, row)
	}
	output := map[string]any{
		"schema_version":                      1,
		"purpose":                             "offline candidate discovery for NEMC native placement verification; not a runtime capability allowlist",
		"source":                              map[string]any{"repository": "neomega-blocks", "git_revision": strings.TrimSpace(string(revision)), "git_dirty": len(gitStatus) != 0, "files": sources, "declared_generator_target_versions": declaredTargets, "version_evidence": "generator filenames only; preset binary contains no self-describing version metadata", "java_input_scope": "source_gen.py combines historical Java versions; outputs may downgrade or merge universal states"},
		"native_registry":                     map[string]any{"file": filepath.Base(*nativePath), "sha256": nativeHash, "record_count": len(native.Blocks), "version_evidence": "dump filename; independently dumped NEMC registry"},
		"summary":                             map[string]any{"bedrock_uibi_output_count": bedrockRecordCount, "java_uibi_output_count": javaRecordCount, "all_name_count": len(names), "candidate_name_count": len(candidates), "native_candidate_name_count": len(nativeCandidates), "native_only_name_count": len(nativeOnly), "mapping_only_name_count": len(mappingOnly), "status_counts": statusCounts, "java_waterlogged_value_types": waterloggedValueTypes, "invalid_java_waterlogged_values": invalidWaterloggedValues, "observed_java_property_keys": javaPropertyKeys},
		"limitations":                         []string{"Java waterlogged is candidate evidence, not proof of Bedrock or NEMC support.", "Absence of Java waterlogged is not proof that a Bedrock block cannot coexist with water.", "Exact UIBI joins can include downgraded target blocks; inspect universal/Java/Bedrock names before testing.", "The Bedrock converter maps foreground state only; wet/dry universal states may collapse to the same Bedrock output.", "Evidence includes at most two wet and two dry examples per name; counts include all converter output records.", "Native registry name presence does not prove the mapped semantic state is available or waterloggable."},
		"candidate_names":                     candidates,
		"java_reverse_waterlogged_query_hits": reverseProbeHits,
		"additional_sources":                  additionalSources,
		"additional_source_metadata":          additionalSourceMetadata,
		"native_capability_candidate_names":   nativeCapabilityCandidates,
		"java_candidates_rejected_by_all_native_matched_states": javaCandidatesRejectedByMatchedStates,
		"bedrock_capability_audit":                              capabilityStats,
		"java_mapping_audit":                                    javaMappingStats,
		"native_candidate_names":                                nativeCandidates,
		"native_only_names":                                     nativeOnly,
		"mapping_only_names":                                    mappingOnly,
		"blocks":                                                outputRows,
	}
	encoded, err := json.MarshalIndent(output, "", "  ")
	fail(err)
	encoded = append(encoded, '\n')
	fail(os.MkdirAll(filepath.Dir(*outputPath), 0755))
	fail(os.WriteFile(*outputPath, encoded, 0644))
	fmt.Printf("%d candidate names, %d present in native registry; %d native-only and %d mapping-only names\n", len(candidates), len(nativeCandidates), len(nativeOnly), len(mappingOnly))
	fmt.Printf("%s\n", *outputPath)
	for _, name := range []string{"minecraft:acacia_fence", "minecraft:acacia_stairs", "minecraft:stone", "minecraft:water"} {
		if block, found := javaExamples[name]; found {
			fmt.Printf("%s -> %v\n", name, block)
		}
	}
}
