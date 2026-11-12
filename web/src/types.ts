/** Original Buxi types. Reference: ts-tarot-cards' separation of card / suit / spread. */
export type FriendId='feiyue'|'xingche'|'zhiwei';
export type Card={id:string;name:string;kind:string;position:string;reversed:boolean;prompt:string;arcana?:'major'|'minor';suit?:'wands'|'cups'|'swords'|'pentacles'|null;rank?:number;meanings?:{upright:string;reversed:string};source?:{name:string;url:string;revision:string;id:number}};
export type Reference={entry_id:string;citation_id?:string;title:string;text:string;source_id:string;knowledge_version:string;content_kind:string;review_status:string;edition_note?:string;caution?:string;evidence:{source_url?:string;section?:string;line_start?:number;line_end?:number;text_en?:string}[]};
export type Selection={status:'picking'|'complete';total:number;picked:number[];positions:string[]};
export type Reading={id:string;system:'tarot'|'sticks';question:string;spread:string;cards:Card[];created_at:string;interpretation:string;interpretation_source:string;algorithm_version:string;saved:boolean;revealed?:string[];generation_status?:string;knowledge_version?:string;citations?:Reference[];selection?:Selection};
export type Message={role:string;content:string;memory_sources?:string[];citations?:Reference[]};
export type Memory={id:string;friend:FriendId;content:string;source:string;active:boolean};
